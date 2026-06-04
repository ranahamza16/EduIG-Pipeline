import pytest
from src.dashboard.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_manifest_serves_correctly(client):
    response = client.get("/static/manifest.json")
    assert response.status_code == 200
    assert "application/json" in response.mimetype or "application/manifest+json" in response.mimetype
    assert b"EduIG Dashboard" in response.data

def test_service_worker_serves_correctly(client):
    response = client.get("/static/sw.js")
    assert response.status_code == 200
    assert "application/javascript" in response.mimetype or "text/javascript" in response.mimetype
    assert b"CACHE_NAME" in response.data

def test_offline_page_serves_correctly(client):
    response = client.get("/offline.html")
    assert response.status_code == 200
    assert b"You are offline" in response.data

def test_base_html_contains_manifest(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'rel="manifest" href="/static/manifest.json"' in response.data
    assert b'name="theme-color" content="#3b82f6"' in response.data
