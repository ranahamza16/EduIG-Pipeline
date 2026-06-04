import argparse
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config_loader import ConfigSchema
from src.storage import get_successful_targets, init_db


@pytest.fixture
def mock_targets_file(tmp_path):
    targets_file = tmp_path / "targets.csv"
    targets_file.write_text("https://instagram.com/integration_test,false\n")
    return str(targets_file)


@pytest.mark.asyncio
async def test_orchestrator_end_to_end(tmp_path, mock_targets_file):
    """Test the main execution loop end-to-end with mocks."""
    db_path = tmp_path / "test_eduig.db"

    # We patch everything that touches disk or network
    with (
        patch("run.parse_args") as mock_args,
        patch("run.load_config") as mock_load_config,
        patch("run.init_db") as mock_init_db,
        patch("run.BrowserWorker") as mock_browser_class,
        patch("run.read_targets") as mock_read_targets,
        patch("run.RateLimiter") as mock_limiter_class,
        patch("run.save_run"),
        patch("run.save_target_status"),
        patch("run.save_profile"),
        patch("run.get_successful_targets") as mock_get_successful,
    ):

        # 1. Setup mocks
        args = argparse.Namespace(
            config="tests/fixtures/test_settings.yaml",
            dry_run=False,
            resume=None,
            export_csv=False,
            authenticated=False,
            test_login=False,
            dashboard=False,
        )
        mock_args.return_value = args

        mock_config = ConfigSchema()
        mock_load_config.return_value = mock_config

        mock_read_targets.return_value = [("https://instagram.com/integration_test", False)]
        mock_get_successful.return_value = set()

        # Mock RateLimiter
        mock_limiter = MagicMock()
        mock_limiter.acquire = AsyncMock()
        mock_limiter_class.return_value = mock_limiter

        # Mock Browser Worker
        mock_worker_instance = MagicMock()
        mock_worker_instance.extract_public_profile = AsyncMock(
            return_value={
                "graphql": {
                    "user": {
                        "id": "123456789",
                        "biography": "Integration Test Bio",
                        "edge_followed_by": {"count": 1000},
                        "edge_follow": {"count": 500},
                        "edge_owner_to_timeline_media": {"count": 10},
                    }
                }
            }
        )
        mock_browser_class.return_value = mock_worker_instance

        # 2. Run
        from run import main

        await main()

        # 3. Assertions
        mock_worker_instance.extract_public_profile.assert_called_once_with("integration_test")
        mock_limiter.acquire.assert_called_once()
        mock_limiter.record_success.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_dry_run(tmp_path):
    """Test the dry run mode."""
    with (
        patch("run.parse_args") as mock_args,
        patch("run.load_config") as mock_load_config,
        patch("run.read_targets") as mock_read_targets,
        patch("run.RateLimiter") as mock_limiter_class,
        patch("run.init_db"),
        patch("run.save_run"),
        patch("run.save_target_status"),
    ):

        args = argparse.Namespace(
            config="tests/fixtures/test_settings.yaml",
            dry_run=True,
            resume=None,
            export_csv=False,
            authenticated=False,
            test_login=False,
            dashboard=False,
        )
        mock_args.return_value = args

        mock_config = ConfigSchema()
        mock_load_config.return_value = mock_config

        mock_read_targets.return_value = [("https://instagram.com/integration_test", False)]

        mock_limiter = MagicMock()
        mock_limiter.acquire = AsyncMock()
        mock_limiter_class.return_value = mock_limiter

        # Run
        from run import main

        await main()

        # Assertions
        # In dry-run, acquire shouldn't be called because the target is marked as skipped
        mock_limiter.acquire.assert_not_called()
