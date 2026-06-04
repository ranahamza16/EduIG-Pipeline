#!/usr/bin/env python3
"""
WARNING: This script uses REAL Instagram credentials from .env
and hits live API endpoints.

Account ban/lock risk is possible. Run at your own risk.
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime

from dotenv import load_dotenv

# Ensure the parent directory is in the path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.auth.session_manager import AuthenticatedSessionManager
from src.auth.authenticated_worker import AuthenticatedWorker
from src.normalizer import normalize_authenticated_data
from src.logger import get_logger

async def main():
    print("=" * 60)
    print("WARNING: This uses REAL Instagram credentials and hits live API")
    print("Account ban/lock risk. Run at your own risk.")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(description="Test authenticated extraction")
    parser.add_argument("username", nargs="?", help="Instagram username to extract")
    args = parser.parse_args()

    load_dotenv()
    
    username = args.username or os.environ.get("TEST_USERNAME")
    if not username:
        print("Error: Must provide a username as argument or set TEST_USERNAME in .env")
        sys.exit(1)

    logger = get_logger()
    config = {}
    
    session_manager = AuthenticatedSessionManager(config)
    
    try:
        print("\n[1] Initializing session manager and logging in...")
        await session_manager.initialize()
        
        if not session_manager.is_authenticated:
            print("Failed to authenticate. Exiting.")
            sys.exit(1)
            
        print("[2] Session established. Extracting profile data...")
        worker = AuthenticatedWorker(session_manager, config, logger)
        
        # Take a screenshot before extraction
        os.makedirs("data/artifacts", exist_ok=True)
        screenshot_path = "data/artifacts/authenticated_extraction_screenshot.png"
        page = await session_manager.stealth_browser.new_page()
        await page.goto(f"https://www.instagram.com/{username}/")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=screenshot_path)
        await page.close()
        print(f"    -> Screenshot saved to {screenshot_path}")

        profile = await worker.extract_profile(username)
        posts = await worker.extract_posts(username, limit=3)
        
        # Normalize to compute avg_engagement_rate and scrub PII
        # Since we just want to show the output for this test, we can display exactly what we parsed.
        profile_norm, posts_norm = normalize_authenticated_data(profile, posts)
        
        if not profile_norm:
            print("Failed to extract or normalize profile.")
            sys.exit(1)

        print("\n[3] Extraction Complete. Results:")
        print(f"Username: {profile.username}")
        print(f"Exact Followers: {profile.exact_followers}")
        print(f"Exact Following: {profile.exact_following}")
        print(f"Exact Posts: {profile.exact_posts_count}")
        
        avg_er_str = f"{profile_norm.avg_engagement_rate * 100:.2f}%" if profile_norm.avg_engagement_rate is not None else "0.00%"
        print(f"Average Engagement Rate: {avg_er_str}")
        
        # Build JSON payload
        payload = {
            "username": profile.username,
            "exact_followers": profile.exact_followers,
            "exact_following": profile.exact_following,
            "exact_posts_count": profile.exact_posts_count,
            "avg_engagement_rate": avg_er_str,
            "posts": [
                {
                    "post_id": p.post_id,
                    "likes": p.likes,
                    "comments": p.comments,
                    "engagement_rate": f"{p.engagement_rate * 100:.2f}%" if p.engagement_rate is not None else "0.00%",
                    "posted_at": p.timestamp.isoformat() if p.timestamp else None
                } for p in posts_norm
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        result_path = "data/artifacts/authenticated_extraction_result.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            
        print(f"\n[4] Data saved to {result_path}")
        
    except Exception as e:
        print(f"\n[!] Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("\n[5] Cleaning up session...")
        await session_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
