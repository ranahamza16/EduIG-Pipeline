"""SQLite Storage Module for EduIG-Pipeline.

Handles persisting validated Pydantic schemas (profiles, posts, runs, targets)
to a local SQLite database safely using UPSERT operations.
"""

import contextlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get("EDUIG_DB_PATH", "data/eduig.db")

def _connect(db_path: str) -> sqlite3.Connection:
    if db_path == ":memory:":
        return sqlite3.connect("file::memory:?cache=shared", uri=True)
    return sqlite3.connect(db_path)

from src.schemas import (
    AuthenticatedProfileSchema,
    PostSchema,
    ProfileSchema,
    RunSchema,
    TargetSchema,
)


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the SQLite database and create tables if missing.

    Args:
        db_path: Path to the SQLite database file.
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with contextlib.closing(_connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            # Create Profiles Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    full_name TEXT,
                    is_verified BOOLEAN,
                    is_private BOOLEAN,
                    bio TEXT,
                    followers INTEGER,
                    following INTEGER,
                    posts_count INTEGER,
                    extracted_at TEXT NOT NULL,
                    source TEXT NOT NULL
                )
                """)

            # Create Posts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    post_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    shortcode TEXT NOT NULL,
                    type TEXT NOT NULL,
                    likes INTEGER,
                    comments INTEGER,
                    timestamp TEXT,
                    hashtags TEXT,
                    engagement_rate REAL
                )
                """)

            # Migrate profiles table if needed
            cursor.execute("PRAGMA table_info(profiles)")
            columns = {col[1] for col in cursor.fetchall()}
            if "exact_followers" not in columns:
                cursor.execute("ALTER TABLE profiles ADD COLUMN exact_followers INTEGER")
                cursor.execute("ALTER TABLE profiles ADD COLUMN exact_following INTEGER")
                cursor.execute("ALTER TABLE profiles ADD COLUMN exact_posts_count INTEGER")
                cursor.execute("ALTER TABLE profiles ADD COLUMN avg_engagement_rate REAL")
                cursor.execute("ALTER TABLE profiles ADD COLUMN profile_picture_url TEXT")
                cursor.execute("ALTER TABLE profiles ADD COLUMN business_category TEXT")
            if "is_private" not in columns:
                cursor.execute("ALTER TABLE profiles ADD COLUMN is_private BOOLEAN")

            # Migrate posts table if needed
            cursor.execute("PRAGMA table_info(posts)")
            columns_posts = {col[1] for col in cursor.fetchall()}
            if "posted_at" not in columns_posts:
                cursor.execute("ALTER TABLE posts ADD COLUMN posted_at TEXT")
                cursor.execute("ALTER TABLE posts ADD COLUMN location TEXT")

            # Create Runs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    targets_count INTEGER,
                    success_count INTEGER
                )
                """)

            # Create Target Status Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS target_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    UNIQUE(run_id, target_url)
                )
                """)

            # Create Audit Log Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    message TEXT,
                    timestamp TEXT NOT NULL
                )
                """)


def save_profile(profile: ProfileSchema, db_path: str = DEFAULT_DB_PATH) -> None:
    """Save or update a ProfileSchema in the database.

    Args:
        profile: The validated ProfileSchema to save.
        db_path: Path to the SQLite database file.
    """
    with contextlib.closing(_connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            # We convert datetime to ISO format string for SQLite
            extracted_at = profile.extracted_at.isoformat()

            if isinstance(profile, AuthenticatedProfileSchema):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO profiles (
                        profile_id, username, full_name, is_verified, is_private, bio, followers,
                        following, posts_count, extracted_at, source,
                        exact_followers, exact_following, exact_posts_count,
                        avg_engagement_rate, profile_picture_url, business_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.profile_id,
                        profile.username,
                        profile.full_name,
                        profile.is_verified,
                        profile.is_private,
                        profile.bio,
                        (
                            profile.followers
                            if profile.followers is not None
                            else getattr(profile, "exact_followers", None)
                        ),
                        (
                            profile.following
                            if profile.following is not None
                            else getattr(profile, "exact_following", None)
                        ),
                        (
                            profile.posts_count
                            if profile.posts_count is not None
                            else getattr(profile, "exact_posts_count", None)
                        ),
                        extracted_at,
                        profile.source,
                        profile.exact_followers,
                        profile.exact_following,
                        profile.exact_posts_count,
                        profile.avg_engagement_rate,
                        profile.profile_picture_url,
                        profile.business_category,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO profiles (
                        profile_id, username, full_name, is_verified, is_private, bio, followers,
                        following, posts_count, extracted_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.profile_id,
                        profile.username,
                        profile.full_name,
                        profile.is_verified,
                        profile.is_private,
                        profile.bio,
                        profile.followers,
                        profile.following,
                        profile.posts_count,
                        extracted_at,
                        profile.source,
                    ),
                )


def save_post(post: PostSchema, db_path: str = DEFAULT_DB_PATH) -> None:
    """Save or update a PostSchema in the database.

    Args:
        post: The validated PostSchema to save.
        db_path: Path to the SQLite database file.
    """
    with contextlib.closing(_connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            timestamp = post.timestamp.isoformat() if post.timestamp else None
            posted_at = (
                post.posted_at.isoformat()
                if hasattr(post, "posted_at") and post.posted_at
                else None
            )

            # Serialize hashtags list to JSON string
            hashtags_json = json.dumps(post.hashtags)

            cursor.execute(
                """
                INSERT OR REPLACE INTO posts (
                    post_id, profile_id, shortcode, type,
                    likes, comments, timestamp, hashtags, engagement_rate,
                    posted_at, location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.post_id,
                    post.profile_id,
                    post.shortcode,
                    post.type,
                    post.likes,
                    post.comments,
                    timestamp,
                    hashtags_json,
                    post.engagement_rate,
                    posted_at,
                    getattr(post, "location", None),
                ),
            )


def save_run(run: RunSchema, db_path: str = DEFAULT_DB_PATH) -> None:
    """Save or update a RunSchema in the database."""
    with contextlib.closing(_connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            completed_at = run.completed_at.isoformat() if run.completed_at else None

            cursor.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, started_at, completed_at, targets_count, success_count
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.started_at.isoformat(),
                    completed_at,
                    run.targets_count,
                    run.success_count,
                ),
            )


def save_target_status(target: TargetSchema, db_path: str = DEFAULT_DB_PATH) -> None:
    """Save or update a TargetSchema in the database."""
    with contextlib.closing(_connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO target_status (
                    id, run_id, target_url, status, error_message
                ) VALUES (
                    (SELECT id FROM target_status WHERE run_id=? AND target_url=?),
                    ?, ?, ?, ?
                )
                """,
                (
                    target.run_id,
                    target.target_url,
                    target.run_id,
                    target.target_url,
                    target.status,
                    target.error_message,
                ),
            )


def get_successful_targets(run_id: str, db_path: str = DEFAULT_DB_PATH) -> set[str]:
    """Retrieve all successful target URLs for a given run ID."""
    with contextlib.closing(_connect(db_path)) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT target_url FROM target_status WHERE run_id=? AND status='success'",
                (run_id,),
            )
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            return set()


def get_profile_extracted_at(profile_id: str, db_path: str = DEFAULT_DB_PATH) -> datetime | None:
    """Retrieve the extraction timestamp of an existing profile."""
    with contextlib.closing(_connect(db_path)) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT extracted_at FROM profiles WHERE profile_id=?", (profile_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return datetime.fromisoformat(row[0])
            return None
        except sqlite3.OperationalError:
            return None


import csv
import os


def export_to_csv(db_path: str = DEFAULT_DB_PATH, export_dir: str = "data/exports") -> str | None:
    """Export profiles and posts to CSV with formatted fields."""
    if db_path != ":memory:" and not os.path.exists(db_path):
        return None

    os.makedirs(export_dir, exist_ok=True)
    profiles_path = os.path.join(export_dir, "profiles_export.csv")
    posts_path = os.path.join(export_dir, "posts_export.csv")

    with contextlib.closing(_connect(db_path)) as conn:
        cursor = conn.cursor()

        # Export Profiles
        try:
            cursor.execute("SELECT * FROM profiles")
            headers = [desc[0] for desc in cursor.description]

            er_idx = (
                headers.index("avg_engagement_rate") if "avg_engagement_rate" in headers else -1
            )

            with open(profiles_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for row in cursor.fetchall():
                    row_list = list(row)
                    if er_idx >= 0 and row_list[er_idx] is not None:
                        row_list[er_idx] = f"{row_list[er_idx] * 100:.2f}%"
                    writer.writerow(row_list)
        except sqlite3.OperationalError:
            pass

        # Export Posts
        try:
            cursor.execute("SELECT * FROM posts")
            headers = [desc[0] for desc in cursor.description]

            er_idx = headers.index("engagement_rate") if "engagement_rate" in headers else -1

            with open(posts_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for row in cursor.fetchall():
                    row_list = list(row)
                    if er_idx >= 0 and row_list[er_idx] is not None:
                        row_list[er_idx] = f"{row_list[er_idx] * 100:.2f}%"
                    writer.writerow(row_list)
        except sqlite3.OperationalError:
            pass

    return profiles_path
