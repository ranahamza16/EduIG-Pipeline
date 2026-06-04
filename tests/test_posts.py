"""Test post extraction logic."""

import pytest

from src.browser_worker import BrowserWorker
from src.config_loader import ConfigSchema


@pytest.fixture
def mock_config():
    """Return a mock configuration."""
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
    )


def test_extract_recent_posts(mock_config):
    """Test BrowserWorker.extract_recent_posts with a mocked payload."""
    worker = BrowserWorker(mock_config)

    # Fake raw GraphQL data structure
    fake_raw_data = {
        "graphql": {
            "user": {
                "edge_owner_to_timeline_media": {
                    "edges": [
                        {
                            "node": {
                                "id": "123",
                                "shortcode": "ABC",
                                "__typename": "GraphImage",
                                "edge_media_preview_like": {"count": 500},
                                "edge_media_to_comment": {"count": 20},
                                "taken_at_timestamp": 1600000000,
                                "edge_media_to_caption": {
                                    "edges": [{"node": {"text": "Hello world! #testing"}}]
                                },
                            }
                        },
                        {
                            "node": {
                                "id": "124",
                                "shortcode": "DEF",
                                "__typename": "GraphVideo",
                                "edge_media_preview_like": {"count": 1000},
                                "edge_media_to_comment": {"count": 50},
                                "taken_at_timestamp": 1600000001,
                                "edge_media_to_caption": {},
                            }
                        },
                    ]
                }
            }
        }
    }

    posts = worker.extract_recent_posts("test_user", fake_raw_data)

    assert len(posts) == 2

    p1 = posts[0]
    assert p1["id"] == "123"
    assert p1["shortcode"] == "ABC"
    assert p1["__typename"] == "GraphImage"
    assert p1["edge_media_preview_like"]["count"] == 500

    p2 = posts[1]
    assert p2["shortcode"] == "DEF"
    assert p2["__typename"] == "GraphVideo"


def test_extract_recent_posts_empty(mock_config):
    """Test extraction handles empty/missing edges gracefully."""
    worker = BrowserWorker(mock_config)

    assert worker.extract_recent_posts("test_user", {}) == []
    assert worker.extract_recent_posts("test_user", {"graphql": {"user": {}}}) == []


from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_playwright():
    """Mock playwright objects for testing without a real browser."""
    with patch("src.browser_worker.async_playwright") as mock_pw:
        mock_context_manager = AsyncMock()
        mock_pw.return_value = mock_context_manager

        mock_playwright_instance = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_playwright_instance

        mock_browser = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser

        mock_context = AsyncMock()
        mock_browser.new_context.return_value = mock_context

        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page

        yield {
            "playwright": mock_playwright_instance,
            "browser": mock_browser,
            "context": mock_context,
            "page": mock_page,
        }


@pytest.mark.asyncio
async def test_extract_post_success(mock_config, mock_playwright):
    """Test successful post extraction."""
    worker = BrowserWorker(mock_config)
    mock_page = mock_playwright["page"]
    expected_data = {"require": True, "graphql": {"shortcode_media": {"shortcode": "CbXYZ123"}}}
    mock_page.evaluate.return_value = expected_data

    result = await worker.extract_post("CbXYZ123")

    assert result == expected_data
    mock_page.goto.assert_called_once_with(
        "https://www.instagram.com/p/CbXYZ123/", timeout=mock_config.browser.timeout
    )
    mock_playwright["browser"].close.assert_called_once()


@pytest.mark.asyncio
async def test_extract_post_json_fails(mock_config, mock_playwright):
    """Test when json extraction fails for a post."""
    worker = BrowserWorker(mock_config)
    mock_page = mock_playwright["page"]
    mock_page.evaluate.return_value = None

    result = await worker.extract_post("CbXYZ123")
    assert result == {}


@pytest.mark.asyncio
async def test_extract_post_timeout(mock_config, mock_playwright):
    """Test timeout during post extraction."""
    worker = BrowserWorker(mock_config)
    mock_page = mock_playwright["page"]
    mock_page.goto.side_effect = Exception("Navigation Timeout Exceeded")

    result = await worker.extract_post("CbXYZ123")
    assert result == {}
