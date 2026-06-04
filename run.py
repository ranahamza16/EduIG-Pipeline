"""Main Orchestrator for EduIG-Pipeline.

Reads targets from configuration, orchestrates the scraping process,
enforces rate limits, normalizes the data, and persists it to SQLite.
Supports resume and dry-run capabilities.
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Union

import structlog
from pydantic import ValidationError

from src.browser_worker import BrowserWorker
from src.config_loader import load_config
from src.exceptions import (
    CircuitBreakerError,
    PrivateProfileError,
    ProfileNotFoundError,
    RateLimitExceededError,
)
from src.logger import configure_logging, get_logger
from src.normalizer import normalize_post, normalize_profile
from src.rate_limiter import RateLimiter
from src.router import parse_url
from src.schemas import PostSchema, ProfileSchema, RunSchema, TargetSchema
from src.storage import (
    get_successful_targets,
    init_db,
    save_post,
    save_profile,
    save_run,
    save_target_status,
)

# Ensure UTF-8 output
os.environ["PYTHONUTF8"] = "1"


def read_targets(filepath: str) -> list[tuple[str, bool]]:
    """Read target URLs from a CSV file.

    Format: URL,consent_status (e.g. https://instagram.com/user,true)
    If consent_status is missing, defaults to false.
    """
    targets = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split(",")
                    url = parts[0].strip()
                    consent = False
                    if len(parts) > 1:
                        consent = parts[1].strip().lower() in ("true", "1", "yes")
                    targets.append((url, consent))
    except FileNotFoundError:
        return []
    return targets


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="EduIG-Pipeline Extraction Tool")
    parser.add_argument(
        "--config", type=str, default="config/settings.yaml", help="Path to config file"
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate targets without scraping")
    parser.add_argument("--resume", type=str, help="Resume a previous run using its RUN_ID")
    parser.add_argument(
        "--export-csv", action="store_true", help="Export database to CSV after run"
    )
    parser.add_argument(
        "--authenticated", action="store_true", help="Use authenticated session for exact data extraction"
    )
    parser.add_argument(
        "--dashboard", action="store_true", help="Launch local dashboard (read-only)"
    )
    parser.add_argument(
        "--test-login", action="store_true", help="Test Instagram login credentials and exit"
    )
    return parser.parse_args()


async def main() -> None:
    """Main execution loop for the pipeline."""
    args = parse_args()

    # 1. Initialize core systems
    config = load_config(args.config)
    configure_logging(config)
    logger = get_logger()
    audit = structlog.get_logger("audit")
    
    if args.test_login:
        from src.auth.session_manager import AuthenticatedSessionManager
        print("Testing Instagram login...")
        session_manager = AuthenticatedSessionManager(config)
        try:
            await session_manager.initialize()
            await session_manager.login()
            if session_manager.is_authenticated:
                print("Login successful! Session established.")
                sys.exit(0)
            else:
                print("Login failed.")
                sys.exit(1)
        except Exception as e:
            print(f"Login failed with error: {e}")
            sys.exit(1)
        finally:
            await session_manager.close()

    if args.dashboard:
        if args.authenticated:
            print("WARNING: Both --dashboard and --authenticated set. Running dashboard only.")
        print("Launching EduIG Dashboard at http://localhost:5000")
        try:
            from src.dashboard.app import app
            app.run(host="0.0.0.0", port=5000, debug=False)
        except KeyboardInterrupt:
            print("\nShutting down EduIG Dashboard gracefully...")
        sys.exit(0)

    init_db("data/eduig.db")
    limiter = RateLimiter(config)

    # 2. Setup Run Tracking
    run_id = args.resume if args.resume else str(uuid.uuid4())
    run_tracker = RunSchema(run_id=run_id, started_at=datetime.now(timezone.utc))
    save_run(run_tracker)

    logger.info("pipeline_started", run_id=run_id, dry_run=args.dry_run, resuming=bool(args.resume))
    audit.info("pipeline_started", run_id=run_id, dry_run=args.dry_run)
    
    # 2.5 Setup Authentication Session
    session_manager = None
    if args.authenticated:
        from src.auth.session_manager import AuthenticatedSessionManager
        session_manager = AuthenticatedSessionManager(config)
        try:
            await session_manager.initialize()
            await session_manager.login()
            if not session_manager.is_authenticated:
                logger.warning("auth_login_failed_fallback")
                audit.warning("AUTH_LOGIN_FAILED_FALLBACK")
        except Exception as e:
            logger.warning("auth_login_error_fallback", error=str(e))
            audit.warning("AUTH_LOGIN_FAILED_FALLBACK", error=str(e))

    # 3. Read targets
    target_file = "config/targets.csv"
    targets = read_targets(target_file)
    run_tracker.targets_count = len(targets)
    save_run(run_tracker)

    if not targets:
        logger.warning("no_targets_found")
        sys.exit(0)

    # Get previously successful targets if resuming
    successful_targets = get_successful_targets(run_id) if args.resume else set()

    # 4. Spin up the workers
    browser_worker = None
    api_worker = None
    if not args.dry_run:
        browser_worker = BrowserWorker(config, logger)
        if config.api.access_token:
            from src.api_worker import APIWorker

            api_worker = APIWorker(config, logger)

    try:
        for url, consent_granted in targets:
            # Skip if already successful in this run
            if url in successful_targets:
                logger.info("target_already_processed_skipping", url=url)
                continue

            target_status = TargetSchema(run_id=run_id, target_url=url, status="pending")
            save_target_status(target_status)

            try:
                # Routing
                target_info = parse_url(url)
                target_type = target_info.target_type
                target_id = target_info.target_id

                logger.info("processing_target", url=url, type=target_type, target_id=target_id)

                # Dry-Run mode skips network calls
                if args.dry_run:
                    logger.info("dry_run_target_valid", url=url)
                    target_status.status = "skipped"
                    save_target_status(target_status)
                    continue

                # Rate Limiting
                await limiter.acquire()

                # Routing Logic
                worker: Any = browser_worker
                is_auth_worker = False

                if session_manager and session_manager.is_authenticated:
                    from src.router import route_authenticated
                    worker = route_authenticated(session_manager, config, logger)
                    is_auth_worker = worker.__class__.__name__ == "AuthenticatedWorker"
                elif api_worker and consent_granted:
                    worker = api_worker
                    audit.info(
                        "routing_decision",
                        target=target_id,
                        strategy="api",
                        reason="consent_granted",
                    )
                else:
                    audit.info(
                        "routing_decision",
                        target=target_id,
                        strategy="browser",
                        reason="no_consent_or_token",
                    )

                # Extraction
                raw_data = None
                if worker:
                    if target_type == "profile":
                        if is_auth_worker:
                            profile_data = await worker.extract_profile(target_id)
                            posts_data = await worker.extract_posts(target_id, limit=12)
                            raw_data = {"profile": profile_data, "posts": posts_data}
                        else:
                            if asyncio.iscoroutinefunction(worker.extract_public_profile):
                                raw_data = await worker.extract_public_profile(target_id)
                            else:
                                raw_data = worker.extract_public_profile(target_id)
                    elif target_type == "post":
                        if hasattr(worker, "extract_post"):
                            func = getattr(worker, "extract_post")
                            if asyncio.iscoroutinefunction(func):
                                raw_data = await func(target_id)
                            else:
                                raw_data = func(target_id)
                        else:
                            logger.warning("extract_post_not_implemented_yet")
                            continue

                if not raw_data:
                    logger.warning("extraction_failed_no_data", target=target_id)
                    limiter.record_failure()
                    target_status.status = "failed"
                    target_status.error_message = "No data returned"
                    save_target_status(target_status)
                    continue

                # Normalization & Validation
                validated_model: Union[ProfileSchema, PostSchema, None] = None
                auth_posts = []
                
                if target_type == "profile":
                    if is_auth_worker and isinstance(raw_data, dict) and "profile" in raw_data:
                        from src.normalizer import normalize_authenticated_data
                        validated_model, auth_posts = normalize_authenticated_data(
                            raw_data["profile"], raw_data["posts"]
                        )
                    else:
                        validated_model = normalize_profile(raw_data, target_id)
                elif target_type == "post":
                    validated_model = normalize_post(raw_data, target_id)

                # Storage
                if (
                    target_type == "profile"
                    and validated_model
                    and isinstance(validated_model, ProfileSchema)
                ):
                    save_profile(validated_model)

                    # Export artifact for user verification
                    try:
                        import os
                        import json
                        os.makedirs("data/artifacts", exist_ok=True)
                        artifact_path = f"data/artifacts/{target_id}_extracted.json"
                        out_data = validated_model.model_dump(mode="json")
                        if is_auth_worker and auth_posts:
                            out_data["posts"] = [p.model_dump(mode="json") for p in auth_posts]
                        with open(artifact_path, "w") as f:
                            json.dump(out_data, f, indent=2)
                    except Exception as e:
                        logger.error("failed_to_write_artifact", error=str(e))

                    if is_auth_worker and auth_posts:
                        for post_model in auth_posts:
                            try:
                                save_post(post_model)
                            except Exception as e:
                                logger.warning("failed_to_save_post", target=target_id, error=str(e))
                    elif raw_data and "recent_posts" in raw_data:
                        for post_raw in raw_data.get("recent_posts", []):
                            try:
                                post_model = normalize_post(
                                    post_raw,
                                    target_id=post_raw.get("shortcode", "unknown"),
                                    profile_followers=getattr(validated_model, "followers", None),
                                )
                                post_model.profile_id = validated_model.profile_id
                                save_post(post_model)
                            except Exception as e:
                                logger.warning(
                                    "failed_to_save_post", target=target_id, error=str(e)
                                )

                elif (
                    target_type == "post"
                    and validated_model
                    and isinstance(validated_model, PostSchema)
                ):
                    save_post(validated_model)

                # Success
                logger.info("target_completed_successfully", target=target_id)
                audit.info("data_persisted", type=target_type, target=target_id)
                limiter.record_success()

                target_status.status = "success"
                save_target_status(target_status)
                run_tracker.success_count += 1
                save_run(run_tracker)

            except ValueError as e:
                logger.error("invalid_target_url", url=url, error=str(e))
                target_status.status = "failed"
                target_status.error_message = str(e)
                save_target_status(target_status)

            except PrivateProfileError as e:
                logger.warning("profile_is_private_skipping", target=url)
                target_status.status = "skipped"
                target_status.error_message = str(e)
                save_target_status(target_status)

            except ProfileNotFoundError as e:
                logger.error("profile_not_found_404", target=url)
                limiter.record_failure()
                target_status.status = "failed"
                target_status.error_message = str(e)
                save_target_status(target_status)

            except ValidationError as e:
                logger.error("data_validation_failed", target=url, error=str(e))
                limiter.record_failure()
                target_status.status = "failed"
                target_status.error_message = f"Validation Error: {str(e)[:100]}"
                save_target_status(target_status)

            except Exception as e:
                logger.exception("unexpected_extraction_error", target=url, error=str(e))
                is_429 = "429" in str(e) or "Too Many Requests" in str(e)
                limiter.record_failure(is_429=is_429)
                target_status.status = "failed"
                target_status.error_message = f"Unexpected Error: {str(e)[:100]}"
                save_target_status(target_status)

    except RateLimitExceededError as e:
        logger.critical("rate_limit_exceeded_stopping_pipeline", error=str(e))
        audit.error("pipeline_halted_rate_limit", error=str(e))
        sys.exit(1)

    except CircuitBreakerError as e:
        logger.critical("circuit_breaker_tripped_stopping_pipeline", error=str(e))
        audit.error("pipeline_halted_circuit_breaker", error=str(e))
        sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("pipeline_interrupted_by_user")

    finally:
        # Wrap up the run
        if session_manager:
            try:
                await session_manager.close()
            except Exception as e:
                logger.error("session_cleanup_failed", error=str(e))
                
        run_tracker.completed_at = datetime.now(timezone.utc)
        save_run(run_tracker)

        logger.info("pipeline_finished", run_id=run_id, success_count=run_tracker.success_count)

        if args.export_csv:
            import csv
            import os
            import sqlite3
            
            os.makedirs("data/exports", exist_ok=True)
            db_path = "data/eduig.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM profiles")
                with open("data/exports/profiles_export.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([desc[0] for desc in cursor.description])
                    writer.writerows(cursor.fetchall())
                logger.info("export_csv_completed", file="data/exports/profiles_export.csv")
                conn.close()


if __name__ == "__main__":
    asyncio.run(main())
