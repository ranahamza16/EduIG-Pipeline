import pytest
from src.dashboard.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_custom_css_serves_correctly(client):
    response = client.get("/static/css/custom.css")
    assert response.status_code == 200
    assert "text/css" in response.mimetype
    assert b"transition-all" in response.data

def test_base_html_contains_skip_link(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'href="#main-content"' in response.data
    assert b'sr-only focus:not-sr-only' in response.data

def test_buttons_have_focus_classes(client):
    response = client.get("/")
    assert response.status_code == 200
    # Simple regex or string check for focus:ring-2
    assert b'focus:ring-2' in response.data or b'focus:outline-none' in response.data
