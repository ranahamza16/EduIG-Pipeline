"""Integration tests for EduIG-Pipeline.

Validates the end-to-end data flow through the entire orchestration loop
(run.py) by mocking the BrowserWorker and testing the database outputs.
"""

import sqlite3
import sys
from unittest.mock import AsyncMock, patch

import pytest

import run


@pytest.fixture
def mock_env(tmp_path):
    """Setup an isolated temporary environment for the pipeline."""
    # Create fake targets file
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    targets_file = config_dir / "targets.csv"
    targets_file.write_text(
        "https://instagram.com/test_user1/\n"
        "https://instagram.com/test_user2/\n"
        "https://instagram.com/test_user3/\n",
        encoding="utf-8",
    )

    # Create fake config file
    config_file = config_dir / "settings.yaml"
    config_file.write_text("""
rate_limit:
  requests_per_hour: 50
  base_delay: 0.1
  max_retries: 3
  backoff_factor: 2.0
paths:
  raw_data: data/raw
  processed: data/processed
  logs: logs
compliance:
  max_profiles_per_run: 50
  delete_raw_after_days: 7
  require_consent: false
browser:
  headless: true
  timeout: 5000
  viewport_width: 1280
  viewport_height: 800
  user_agent: "Mozilla/5.0"
""")

    db_path = tmp_path / "data" / "eduig.db"
    db_path.parent.mkdir()

    return {
        "targets_file": str(targets_file),
        "config_file": str(config_file),
        "db_path": str(db_path),
        "tmp_path": tmp_path,
    }


@pytest.mark.asyncio
async def test_end_to_end_pipeline(mock_env):
    """Test the full pipeline using a mocked browser."""

    # Fake browser extraction responses
    async def fake_extract(username: str):
        return {
            "graphql": {
                "user": {
                    "id": f"internal_{username}",
                    "biography": (
                        f"Email me at {username}@test.com! "
                        f"Call +1 555-123-4567. "
                        f"Link: linktr.ee/{username}"
                    ),
                    "edge_followed_by": {"count": "10.5K"},
                    "edge_follow": {"count": "500"},
                }
            }
        }

    # Mock the BrowserWorker and configuration paths
    with (
        patch("run.BrowserWorker") as MockWorker,
        patch("run.init_db") as mock_init_db,
        patch("run.save_profile") as mock_save_profile,
        patch("run.save_run") as mock_save_run,
        patch("run.save_target_status") as mock_save_target_status,
        patch("run.get_successful_targets", return_value=set()),
        patch.object(sys, "argv", ["run.py", "--config", mock_env["config_file"]]),
    ):

        # We need the real storage functions but pointing to our test DB
        from src.storage import init_db as real_init_db
        from src.storage import save_profile as real_save_profile
        from src.storage import save_run as real_save_run
        from src.storage import save_target_status as real_save_target_status

        real_init_db(mock_env["db_path"])

        # Route mock calls to real functions with our test DB
        mock_init_db.side_effect = lambda _: real_init_db(mock_env["db_path"])
        mock_save_profile.side_effect = lambda p: real_save_profile(p, mock_env["db_path"])
        mock_save_run.side_effect = lambda r: real_save_run(r, mock_env["db_path"])
        mock_save_target_status.side_effect = lambda t: real_save_target_status(
            t, mock_env["db_path"]
        )

        # Override the hardcoded target_file path inside run.py read_targets
        original_read_targets = run.read_targets

        def patched_read_targets(filepath):
            return original_read_targets(mock_env["targets_file"])

        with patch("run.read_targets", side_effect=patched_read_targets):

            # Setup the mock worker instance
            instance = MockWorker.return_value
            instance.extract_public_profile = AsyncMock()
            instance.extract_public_profile.side_effect = fake_extract

            # Run the orchestration loop
            await run.main()

            # --- VERIFICATION ---

            # 1. Verify Browser was called 3 times
            assert instance.extract_public_profile.call_count == 3

            # 2. Check SQLite DB for Profiles
            conn = sqlite3.connect(mock_env["db_path"])
            cursor = conn.cursor()

            cursor.execute("SELECT profile_id, username, bio, followers FROM profiles")
            profiles = cursor.fetchall()

            assert len(profiles) == 3

            # 3. Verify Normalization, Coercion, and Compliance
            for profile in profiles:
                p_id, username, bio, followers = profile

                # Check coercion
                assert followers == 10500

                # Check compliance (PII stripping)
                assert "[EMAIL_REMOVED]" in bio
                assert "[PHONE_REMOVED]" in bio
                assert "[LINK_REMOVED]" in bio

                # Ensure original PII is entirely gone
                assert "test.com" not in bio
                assert "555-123" not in bio
                assert "linktr.ee" not in bio

            # 4. Check Runs Tracker
            cursor.execute("SELECT targets_count, success_count FROM runs")
            runs = cursor.fetchall()
            assert len(runs) == 1
            assert runs[0][0] == 3  # 3 targets processed
            assert runs[0][1] == 3  # 3 targets succeeded

            # 5. Check Target Status
            cursor.execute("SELECT target_url, status FROM target_status")
            statuses = cursor.fetchall()
            assert len(statuses) == 3
            for status in statuses:
                assert status[1] == "success"

            conn.close()
