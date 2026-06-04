import json
import sqlite3
from pathlib import Path
from typing import Any

from src.dashboard.db import get_db_connection


def get_stats(db_path: str = "data/eduig.db") -> dict[str, Any]:
    """Get overall statistics for the dashboard."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM profiles")
        total_profiles = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM posts")
        total_posts = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT AVG(avg_engagement_rate) as avg_engagement "
            "FROM profiles WHERE avg_engagement_rate IS NOT NULL"
        )
        avg_engagement_row = cursor.fetchone()
        avg_engagement = avg_engagement_row["avg_engagement"] if avg_engagement_row else 0.0

        cursor.execute("SELECT MAX(started_at) as last_run FROM runs")
        last_run_row = cursor.fetchone()
        last_run = last_run_row["last_run"] if last_run_row else None

        # Follower distribution for histogram
        # We bucket followers into generic ranges
        cursor.execute("""
            SELECT
                CASE
                    WHEN followers < 1000 THEN '0-1K'
                    WHEN followers >= 1000 AND followers < 10000 THEN '1K-10K'
                    WHEN followers >= 10000 AND followers < 100000 THEN '10K-100K'
                    WHEN followers >= 100000 AND followers < 1000000 THEN '100K-1M'
                    ELSE '1M+'
                END as bucket,
                COUNT(*) as count
            FROM profiles
            GROUP BY bucket
        """)
        follower_dist = cursor.fetchall()

        return {
            "total_profiles": total_profiles,
            "total_posts": total_posts,
            "avg_engagement_rate": avg_engagement,
            "last_run": last_run,
            "follower_distribution": follower_dist,
        }


def get_profiles(
    db_path: str = "data/eduig.db",
    page: int = 1,
    per_page: int = 25,
    search: str = "",
    sort_by: str = "extracted_at",
    order: str = "desc",
) -> dict[str, Any]:
    """Get a paginated list of profiles with optional search and sort."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        allowed_sorts = [
            "username",
            "followers",
            "exact_followers",
            "posts_count",
            "extracted_at",
            "avg_engagement_rate",
            "source",
        ]
        if sort_by not in allowed_sorts:
            sort_by = "extracted_at"

        order = "ASC" if order.lower() == "asc" else "DESC"
        offset = (page - 1) * per_page

        query = "SELECT * FROM profiles"
        count_query = "SELECT COUNT(*) as total FROM profiles"
        params: list[Any] = []

        if search:
            query += " WHERE username LIKE ? OR bio LIKE ?"
            count_query += " WHERE username LIKE ? OR bio LIKE ?"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        query += f" ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"

        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]

        params.extend([per_page, offset])
        cursor.execute(query, params)
        profiles = cursor.fetchall()

        return {
            "data": profiles,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }


def get_profile_detail(profile_id: str, db_path: str = "data/eduig.db") -> dict[str, Any] | None:
    """Get details for a specific profile and its posts."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE profile_id = ? OR username = ?", (profile_id, profile_id))
        profile = cursor.fetchone()

        if not profile:
            return None

        actual_profile_id = profile["profile_id"]
        cursor.execute(
            "SELECT * FROM posts WHERE profile_id = ? ORDER BY timestamp DESC", (actual_profile_id,)
        )
        posts = cursor.fetchall()

        # Parse hashtags JSON
        for post in posts:
            if post["hashtags"]:
                try:
                    post["hashtags"] = json.loads(post["hashtags"])
                except Exception:
                    post["hashtags"] = []
            else:
                post["hashtags"] = []

        return {"profile": profile, "posts": posts}


def get_compliance_logs(
    db_path: str = "data/eduig.db", log_path: str = "data/logs/audit.log"
) -> dict[str, Any]:
    """Get compliance audit logs from both flat files and SQLite."""
    logs = []

    # 1. Parse from flat file (structlog format)
    log_file = Path(log_path)
    if log_file.exists():
        with open(log_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    logs.append(
                        {
                            "timestamp": entry.get("timestamp", ""),
                            "event": entry.get("event", ""),
                            "target": entry.get("target", "N/A"),
                            "level": entry.get("level", ""),
                            "details": {
                                k: v
                                for k, v in entry.items()
                                if k not in ["timestamp", "event", "target", "level"]
                            },
                        }
                    )
                except json.JSONDecodeError:
                    pass

    # Sort flat file logs by timestamp DESC
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    # 2. Get run summary from SQLite
    runs = []
    if Path(db_path).exists():
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 50")
                runs = cursor.fetchall()
            except sqlite3.OperationalError:
                pass

    return {"audit_events": logs[:500], "runs": runs}  # Limit to last 500 events
