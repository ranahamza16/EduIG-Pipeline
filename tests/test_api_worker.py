"""Test API worker logic with mocked HTTP responses."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.api_worker import APIWorker
from src.config_loader import ConfigSchema
from src.exceptions import RateLimitExceededError


@pytest.fixture
def mock_config():
    """Return a mock configuration with an access token."""
    return ConfigSchema(
        rate_limit={
            "requests_per_hour": 50,
            "base_delay": 0.1,
            "max_retries": 3,
            "backoff_factor": 2.0,
        },
        paths={"raw_data": "data/raw", "processed": "data/processed", "logs": "logs"},
        compliance={
            "max_profiles_per_run": 50,
            "delete_raw_after_days": 7,
            "require_consent": False,
        },
        browser={
            "headless": True,
            "timeout": 5000,
            "viewport_width": 1280,
            "viewport_height": 800,
            "user_agent": "test",
        },
        api={
            "base_url": "https://graph.fake.com",
            "timeout": 30.0,
            "max_connections": 10,
            "access_token": "FAKE_TOKEN",
        },
    )


@patch("httpx.AsyncClient.get")
def test_extract_public_profile_success(mock_get, mock_config):
    """Test successful API profile extraction."""
    worker = APIWorker(mock_config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(
        return_value={
            "username": "test_user",
            "biography": "Hello from API!",
            "followers_count": 1000,
            "follows_count": 500,
            "media_count": 10,
        }
    )
    mock_response.headers = {"x-app-usage": "fake_usage"}
    mock_get.return_value = mock_response

    data = worker.extract_public_profile("test_user")

    assert data["username"] == "test_user"
    assert data["followers_count"] == 1000
    assert mock_get.called


@patch("httpx.AsyncClient.get")
def test_extract_recent_posts_success(mock_get, mock_config):
    """Test successful API post extraction."""
    worker = APIWorker(mock_config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(
        return_value={
            "data": [
                {
                    "id": "123",
                    "shortcode": "ABC",
                    "media_type": "IMAGE",
                    "like_count": 100,
                    "comments_count": 10,
                }
            ]
        }
    )
    mock_get.return_value = mock_response

    posts = worker.extract_recent_posts("test_user")

    assert len(posts) == 1
    assert posts[0]["shortcode"] == "ABC"
    assert posts[0]["like_count"] == 100


@patch("httpx.AsyncClient.get")
def test_api_rate_limit_exceeded(mock_get, mock_config):
    """Test API rate limit error raises our custom exception."""
    worker = APIWorker(mock_config)

    mock_response = MagicMock()
    mock_response.status_code = 429

    # httpx raise_for_status mock
    error = httpx.HTTPStatusError(
        "429 Too Many Requests", request=MagicMock(), response=mock_response
    )
    mock_response.raise_for_status.side_effect = error

    mock_get.return_value = mock_response

    with pytest.raises(RateLimitExceededError):
        worker.extract_public_profile("test_user")


@patch("httpx.AsyncClient.get")
def test_api_token_expired(mock_get, mock_config):
    """Test API token expiration triggers refresh_token gracefully."""
    worker = APIWorker(mock_config)

    mock_response = MagicMock()
    mock_response.status_code = 401

    error = httpx.HTTPStatusError("401 Unauthorized", request=MagicMock(), response=mock_response)
    mock_response.raise_for_status.side_effect = error
    mock_get.return_value = mock_response

    with patch.object(worker, "_refresh_token") as mock_refresh:
        data = worker.extract_public_profile("test_user")

        assert data == {}  # Returns empty dict on failure
        assert mock_refresh.called
