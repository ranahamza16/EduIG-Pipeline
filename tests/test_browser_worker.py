from unittest.mock import AsyncMock, patch

import pytest

from src.browser_worker import BrowserWorker
from src.config_loader import ConfigSchema


@pytest.fixture
def config():
    """Return a standard test configuration."""
    return ConfigSchema()


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

        # Configure the mock page to return a title
        mock_page.title.return_value = "Test Title"

        yield {
            "playwright": mock_playwright_instance,
            "browser": mock_browser,
            "context": mock_context,
            "page": mock_page,
        }


@pytest.mark.asyncio
async def test_browser_worker_initialization(config):
    """Test that the worker initializes correctly."""
    worker = BrowserWorker(config)
    assert worker.config == config


@pytest.mark.asyncio
async def test_extract_public_profile_json_strategy(config, mock_playwright):
    """Test successful JSON extraction."""
    worker = BrowserWorker(config)

    # Configure mock to return JSON data
    mock_page = mock_playwright["page"]
    expected_data = {"require": True, "profile_data": {"followers": 1000}}
    mock_page.evaluate.return_value = expected_data

    result = await worker.extract_public_profile("testuser")

    # Assertions
    assert result == expected_data
    mock_page.goto.assert_called_once_with(
        "https://www.instagram.com/testuser/", timeout=config.browser.timeout
    )
    mock_page.wait_for_timeout.assert_called_once_with(3000)
    mock_playwright["browser"].close.assert_called_once()


@pytest.mark.asyncio
async def test_extract_public_profile_fallback_strategy(config, mock_playwright):
    """Test fallback to DOM extraction if JSON strategy returns None."""
    worker = BrowserWorker(config)

    # Configure mock to fail JSON extraction but succeed at DOM extraction
    mock_page = mock_playwright["page"]
    mock_page.evaluate.return_value = None

    mock_element = AsyncMock()
    mock_element.inner_text.return_value = "1M Followers"
    mock_element.get_attribute.return_value = "1M Followers"
    mock_page.query_selector.return_value = mock_element

    result = await worker.extract_public_profile("testuser")

    # Assertions
    assert "username" in result
    assert result["username"] == "testuser"
    assert result["followers"] == "1M Followers"
    assert result["bio"] == "1M Followers"  # Uses same element mock for test

    mock_page.evaluate.assert_called_once()
    assert mock_page.query_selector.call_count == 2
    mock_playwright["browser"].close.assert_called_once()


@pytest.mark.asyncio
async def test_extract_public_profile_timeout(config, mock_playwright):
    """Test handling of navigation timeouts."""
    worker = BrowserWorker(config)

    # Configure mock to raise a Timeout exception
    mock_page = mock_playwright["page"]
    mock_page.goto.side_effect = Exception("Navigation Timeout Exceeded")

    result = await worker.extract_public_profile("timeoutuser")

    # Assertions
    assert result == {}
    mock_playwright["browser"].close.assert_called_once()


@pytest.mark.asyncio
async def test_extract_public_profile_general_exception(config, mock_playwright):
    """Test handling of unexpected exceptions."""
    worker = BrowserWorker(config)

    # Configure mock to raise a general exception during context creation
    mock_browser = mock_playwright["browser"]
    mock_browser.new_context.side_effect = Exception("Unexpected Error")

    result = await worker.extract_public_profile("erroruser")

    # Assertions
    assert result == {}
    mock_playwright["browser"].close.assert_called_once()
