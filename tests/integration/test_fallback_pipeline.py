import asyncio
import os
import sqlite3
import sys
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

import run
from src.schemas import PostSchema, ProfileSchema


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure a clean database."""
    db_path = "data/eduig.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    yield

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_fallback_unauthenticated_pipeline():
    """
    Test the authenticated pipeline falling back gracefully:
    - Login fails
    - Falls back to BrowserWorker
    - Extracts profile with rounded counts
    - Normalization and Storage complete successfully
    """
    # 1. Setup mocked targets
    mock_targets = [("fallbackuser", False)]

    from datetime import datetime, timezone

    mock_profile = {
        "username": "fallbackuser",
        "followers": "25K Followers",
        "raw_title": "Fallback User (@fallbackuser) on Instagram",
        "bio": "Fallback bio",
        "recent_posts": []
    }

    # 3. Apply patches
    with (
        patch.dict("os.environ", {"SESSION_ENCRYPTION_KEY": "bK4z6k_E6m9_y5k7Z3J9W2bN8vX1cM6hF5tG9dK8aZc=", "INSTAGRAM_USERNAME": "u", "INSTAGRAM_PASSWORD": "p"}),
        patch("sys.argv", ["run.py", "--authenticated"]),
        patch("run.read_targets", return_value=mock_targets),
        patch("src.auth.session_manager.AuthenticatedSessionManager.initialize") as mock_init,
        patch("src.auth.session_manager.AuthenticatedSessionManager.login") as mock_login,
        patch("src.auth.session_manager.AuthenticatedSessionManager.is_authenticated", new_callable=PropertyMock, return_value=False, create=True),
        patch(
            "src.browser_worker.BrowserWorker.extract_public_profile", new_callable=AsyncMock
        ) as mock_ext_public,
        patch("src.auth.session_manager.AuthenticatedSessionManager.close") as mock_close,
    ):

        mock_ext_public.return_value = mock_profile

        # 4. Execute main run loop
        await run.main()

        # 5. Verify orchestrator flow
        mock_init.assert_called_once()
        mock_login.assert_called_once()
        mock_ext_public.assert_called_once_with("fallbackuser")
        mock_close.assert_called_once()

    # 6. Verify Database State
    db_path = "data/eduig.db"
    assert os.path.exists(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Profile assertions
    cursor.execute("SELECT username, followers, exact_followers FROM profiles")
    profile_row = cursor.fetchone()
    assert profile_row is not None

    u_name, followers, exact_followers = profile_row

    assert u_name == "fallbackuser"
    assert followers == 25000
    assert exact_followers is None

    # Audit log assertions - verify warning was logged
    audit_log_path = "data/logs/audit.log"
    assert os.path.exists(audit_log_path)
    with open(audit_log_path, "r") as f:
        log_content = f.read()
        assert "AUTH_LOGIN_FAILED_FALLBACK" in log_content

    conn.close()
