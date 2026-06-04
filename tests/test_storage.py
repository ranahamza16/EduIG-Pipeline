import contextlib
import json
import sqlite3
from datetime import datetime, timezone

import pytest

from src.schemas import PostSchema, ProfileSchema
from src.storage import init_db, save_post, save_profile


@pytest.fixture
def memory_db():
    """Fixture that provides an initialized in-memory SQLite database path."""
    import os
    import tempfile

    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    init_db(temp_path)

    yield temp_path

    # Cleanup
    try:
        os.remove(temp_path)
    except OSError:
        pass


from src.schemas import AuthenticatedProfileSchema
from src.storage import export_to_csv, get_profile_extracted_at


def test_authenticated_save_and_load(memory_db):
    """Test saving an authenticated profile with exact counts."""
    profile = AuthenticatedProfileSchema(
        profile_id="auth1",
        username="auth_user",
        bio="Test Bio",
        followers=1000,
        following=500,
        posts_count=100,
        extracted_at=datetime.now(timezone.utc),
        source="api",
        exact_followers=1000,
        exact_following=500,
        exact_posts_count=100,
        avg_engagement_rate=0.05,
    )

    # Needs db init
    init_db(memory_db)
    save_profile(profile, memory_db)

    extracted = get_profile_extracted_at("auth1", memory_db)
    assert extracted is not None
    assert extracted == profile.extracted_at

    with contextlib.closing(sqlite3.connect(memory_db)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT exact_followers, avg_engagement_rate FROM profiles WHERE profile_id='auth1'"
        )
        row = cursor.fetchone()
        assert row[0] == 1000
        assert row[1] == 0.05


def test_export_csv(memory_db):
    """Test CSV export functionality formats percentage and saves fields."""
    profile = AuthenticatedProfileSchema(
        profile_id="auth2",
        username="auth_user2",
        followers=2000,
        following=1000,
        posts_count=200,
        extracted_at=datetime.now(timezone.utc),
        source="api",
        exact_followers=2000,
        exact_following=1000,
        exact_posts_count=200,
        avg_engagement_rate=0.1234,
    )
    post = PostSchema(
        post_id="p2",
        profile_id="auth2",
        shortcode="s2",
        type="image",
        likes=100,
        comments=0,
        engagement_rate=0.4567,
    )

    init_db(memory_db)
    save_profile(profile, memory_db)
    save_post(post, memory_db)

    export_dir = "data/test_exports"
    csv_path = export_to_csv(memory_db, export_dir)
    assert csv_path is not None
    import os

    assert os.path.exists(csv_path)

    # Read CSV and check formatting
    import csv

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["avg_engagement_rate"] == "12.34%"
        assert rows[0]["exact_followers"] == "2000"

    posts_csv_path = os.path.join(export_dir, "posts_export.csv")
    with open(posts_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["engagement_rate"] == "45.67%"


def test_init_db(memory_db):
    """Test that database tables are created correctly."""
    with contextlib.closing(sqlite3.connect(memory_db)) as conn:
        cursor = conn.cursor()

        # Check profiles table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'")
        assert cursor.fetchone() is not None

        # Check posts table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        assert cursor.fetchone() is not None


def test_save_profile(memory_db):
    """Test saving and upserting a profile."""
    # 1. Create a profile
    profile = ProfileSchema(
        profile_id="u123",
        username="hash123",
        bio="Test Bio",
        followers=100,
        following=50,
        posts_count=10,
        extracted_at=datetime.now(timezone.utc),
        source="browser",
    )

    # Save it
    save_profile(profile, db_path=memory_db)

    # Verify in DB
    with contextlib.closing(sqlite3.connect(memory_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT followers, bio FROM profiles WHERE profile_id='u123'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 100
        assert row[1] == "Test Bio"

    # 2. Update the profile (UPSERT)
    profile.followers = 200
    save_profile(profile, db_path=memory_db)

    # Verify UPSERT worked
    with contextlib.closing(sqlite3.connect(memory_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT followers FROM profiles WHERE profile_id='u123'")
        row = cursor.fetchone()
        assert row[0] == 200

        # Ensure it didn't create a second row
        cursor.execute("SELECT COUNT(*) FROM profiles")
        count = cursor.fetchone()[0]
        assert count == 1


def test_save_post(memory_db):
    """Test saving a post with JSON serialization for hashtags."""
    # 1. Create a post
    post = PostSchema(
        post_id="p456",
        profile_id="u123",
        shortcode="XYZ",
        type="image",
        likes=5000,
        comments=120,
        timestamp=datetime.now(timezone.utc),
        hashtags=["nature", "photography"],
    )

    # Save it
    save_post(post, db_path=memory_db)

    # Verify in DB
    with contextlib.closing(sqlite3.connect(memory_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT likes, hashtags FROM posts WHERE post_id='p456'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 5000

        # Verify hashtags were serialized as JSON
        tags = json.loads(row[1])
        assert isinstance(tags, list)
        assert len(tags) == 2
        assert "nature" in tags


def test_save_run_and_target_status(memory_db):
    """Test saving RunSchema and TargetSchema and retrieving successful targets."""
    from src.schemas import RunSchema, TargetSchema
    from src.storage import get_successful_targets, save_run, save_target_status

    # Save a run
    run = RunSchema(run_id="run_test", targets_count=10, success_count=5)
    save_run(run, db_path=memory_db)

    with contextlib.closing(sqlite3.connect(memory_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT targets_count FROM runs WHERE run_id='run_test'")
        assert cursor.fetchone()[0] == 10

    # Save target statuses
    t1 = TargetSchema(run_id="run_test", target_url="https://url1", status="success")
    t2 = TargetSchema(
        run_id="run_test", target_url="https://url2", status="failed", error_message="timeout"
    )

    save_target_status(t1, db_path=memory_db)
    save_target_status(t2, db_path=memory_db)

    # Test retrieval
    success = get_successful_targets("run_test", db_path=memory_db)
    assert len(success) == 1
    assert "https://url1" in success
