import asyncio
import csv
import json
import os
import sqlite3
import sys
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

import run
from src.schemas import AuthenticatedProfileSchema, PostSchema


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure a clean database and exports directory for each test."""
    db_path = "data/eduig.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    export_path = "data/exports/profiles_export.csv"
    if os.path.exists(export_path):
        os.remove(export_path)

    yield

    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(export_path):
        os.remove(export_path)


@pytest.mark.asyncio
async def test_full_authenticated_pipeline():
    """
    Test the complete authenticated pipeline end-to-end:
    - Login success
    - Extract profile with exact counts and PII
    - Extract posts
    - Normalization (PII scrubbing, hashing)
    - Database storage
    - CSV export
    """
    # 1. Setup mocked targets
    mock_targets = [("testuser", False)]

    # 2. Setup mocked extraction data
    from datetime import datetime, timezone

    mock_profile = AuthenticatedProfileSchema(
        profile_id="123456",
        username="testuser",
        exact_followers=10000,
        exact_following=500,
        exact_posts_count=50,
        bio="Contact me at myemail@test.com or call 555-1234",
        is_private=False,
        is_verified=True,
        profile_picture_url="http://example.com/pic.jpg",
        business_category="Creators",
        avg_engagement_rate=None,  # will be calculated
        source="api",
    )

    mock_posts = [
        PostSchema(
            post_id="post1",
            profile_id="123456",
            type="image",
            shortcode="post1",
            likes=1000,
            comments=100,
            caption="Hello world",
            timestamp=datetime.now(timezone.utc),
            engagement_rate=0.11,
        ),
        PostSchema(
            post_id="post2",
            profile_id="123456",
            type="image",
            shortcode="post2",
            likes=500,
            comments=50,
            caption="Another post",
            timestamp=datetime.now(timezone.utc),
            engagement_rate=0.055,
        ),
    ]

    # 3. Apply patches
    with (
        patch.dict("os.environ", {"SESSION_ENCRYPTION_KEY": "bK4z6k_E6m9_y5k7Z3J9W2bN8vX1cM6hF5tG9dK8aZc=", "INSTAGRAM_USERNAME": "u", "INSTAGRAM_PASSWORD": "p"}),
        patch("sys.argv", ["run.py", "--authenticated", "--export-csv"]),
        patch("run.read_targets", return_value=mock_targets),
        patch("src.auth.session_manager.AuthenticatedSessionManager.initialize") as mock_init,
        patch("src.auth.session_manager.AuthenticatedSessionManager.login") as mock_login,
        patch("src.auth.session_manager.AuthenticatedSessionManager.is_authenticated", new_callable=PropertyMock, return_value=True, create=True),
        patch(
            "src.auth.authenticated_worker.AuthenticatedWorker.extract_profile",
            new_callable=AsyncMock,
        ) as mock_ext_prof,
        patch(
            "src.auth.authenticated_worker.AuthenticatedWorker.extract_posts",
            new_callable=AsyncMock,
        ) as mock_ext_posts,
        patch("src.auth.session_manager.AuthenticatedSessionManager.close") as mock_close,
    ):

        mock_ext_prof.return_value = mock_profile
        mock_ext_posts.return_value = mock_posts

        # 4. Execute main run loop
        await run.main()

        # 5. Verify orchestrator flow
        mock_init.assert_called_once()
        mock_login.assert_called_once()
        mock_ext_prof.assert_called_once_with("testuser")
        mock_ext_posts.assert_called_once_with("testuser", limit=12)
        mock_close.assert_called_once()

    # 6. Verify Database State
    db_path = "data/eduig.db"
    assert os.path.exists(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Profile assertions
    cursor.execute(
        "SELECT username, bio, exact_followers, exact_following, exact_posts_count, avg_engagement_rate FROM profiles"
    )
    profile_row = cursor.fetchone()
    assert profile_row is not None

    # Verify username 
    assert profile_row[0] != "testuser"
    assert len(profile_row[0]) == 64

    # Verify PII stripped from bio
    bio = profile_row[1]
    assert "test.com" not in bio
    assert "555-1234" not in bio

    # Verify exact counts
    assert profile_row[2] == 10000
    assert profile_row[3] == 500
    assert profile_row[4] == 50
    assert profile_row[5] == pytest.approx(0.0825)

    # Posts assertions
    cursor.execute("SELECT likes, comments, engagement_rate FROM posts")
    posts_rows = cursor.fetchall()
    assert len(posts_rows) == 2
    assert posts_rows[0][0] == 1000
    assert posts_rows[0][1] == 100

    # Audit log assertions
    audit_log_path = "data/logs/audit.log"
    assert os.path.exists(audit_log_path)
    with open(audit_log_path, "r") as f:
        log_content = f.read()
        assert "pipeline_started" in log_content
        assert "data_persisted" in log_content

    conn.close()

    # 7. Verify CSV Export
    csv_path = "data/exports/profiles_export.csv"
    assert os.path.exists(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1

        row = rows[0]
        assert row["exact_followers"] == "10000"
        # Since CSV export format preserves strings exactly as pulled from DB
        # However, avg_engagement_rate might be a float string "0.0825" depending on normalizer implementation
        assert "0.0825" in row["avg_engagement_rate"] or "8.25%" in row["avg_engagement_rate"]
