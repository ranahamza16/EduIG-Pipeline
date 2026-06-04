import pytest
import json
import sqlite3
import os
from unittest.mock import patch

from src.dashboard.app import app
from src.dashboard.db import dict_factory

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    # Create necessary tables
    cursor.execute("CREATE TABLE profiles (profile_id TEXT, username TEXT, bio TEXT, followers INTEGER, posts_count INTEGER, avg_engagement_rate REAL, extracted_at TEXT, source TEXT)")
    cursor.execute("CREATE TABLE posts (post_id TEXT, profile_id TEXT, hashtags TEXT, timestamp TEXT)")
    cursor.execute("CREATE TABLE runs (run_id TEXT, started_at TEXT)")
    
    # Insert mock data
    cursor.execute("INSERT INTO profiles VALUES ('1', 'test_user', 'bio', 5000, 10, 0.05, '2026-06-01', 'api')")
    cursor.execute("INSERT INTO posts VALUES ('p1', '1', '[\"tag\"]', '2026-06-01')")
    cursor.execute("INSERT INTO runs VALUES ('r1', '2026-06-01')")
    
    conn.commit()
    return conn

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_api_stats(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total_profiles"] == 1

def test_api_profiles(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/profiles?page=1&per_page=10&search=test")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] == 1
        assert data["data"][0]["username"] == "test_user"

def test_api_profile_detail_success(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/profile/1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["profile"]["username"] == "test_user"
        assert len(data["posts"]) == 1

def test_api_profile_detail_not_found(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/profile/999")
        assert response.status_code == 404

def test_api_compliance(client, mock_db, tmp_path):
    log_file = tmp_path / "audit.log"
    log_file.write_text('{"timestamp": "2026", "event": "test"}\ninvalid json\n')
    
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        with patch("src.dashboard.queries.Path", return_value=log_file):
            response = client.get("/api/compliance")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data["audit_events"]) == 1

def test_api_export_json(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/export/json")
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        data = json.loads(response.data)
        assert data[0]["username"] == "test_user"

def test_api_export_csv(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/export/csv")
        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert b"username" in response.data
        assert b"test_user" in response.data

def test_api_export_csv_empty(client, mock_db):
    # Empty DB
    empty_db = sqlite3.connect(":memory:")
    empty_db.row_factory = dict_factory
    empty_db.execute("CREATE TABLE profiles (profile_id TEXT, extracted_at TEXT)")
    
    with patch("src.dashboard.queries.get_db_connection", return_value=empty_db):
        response = client.get("/api/export/csv")
        assert response.status_code == 404

def test_api_export_invalid_format(client, mock_db):
    with patch("src.dashboard.queries.get_db_connection", return_value=mock_db):
        response = client.get("/api/export/invalid")
        assert response.status_code == 400

def test_html_routes(client):
    routes = ["/", "/profiles", "/profile/123", "/compliance", "/settings"]
    for route in routes:
        with patch("src.dashboard.app.render_template", return_value="html content"):
            response = client.get(route)
            assert response.status_code == 200

def test_db_dict_factory():
    from src.dashboard.db import get_db_connection
    conn = get_db_connection(":memory:")
    conn.execute("CREATE TABLE t (a TEXT, b INTEGER)")
    conn.execute("INSERT INTO t VALUES ('val', 1)")
    row = conn.execute("SELECT * FROM t").fetchone()
    assert row["a"] == "val"
    assert row["b"] == 1

