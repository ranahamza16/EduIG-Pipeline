from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth.stealth_browser import StealthBrowser


@pytest.fixture
def dummy_fingerprint():
    return {
        "user_agent": "TestUserAgent/1.0",
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-CA",
        "timezone_id": "America/Toronto",
        "hardware_concurrency": 8,
    }


@pytest.mark.asyncio
async def test_stealth_browser_lifecycle(dummy_fingerprint):
    browser = StealthBrowser(fingerprint=dummy_fingerprint)

    # Check fingerprint retrieval
    assert browser.get_fingerprint() == dummy_fingerprint

    # Mock playwright
    with patch("src.auth.stealth_browser.async_playwright") as mock_playwright:
        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright.return_value.start = AsyncMock(return_value=mock_pw_instance)
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Test launch
        context = await browser.launch()

        # Verify launch args
        mock_pw_instance.chromium.launch.assert_called_once()
        launch_kwargs = mock_pw_instance.chromium.launch.call_args.kwargs
        args = launch_kwargs["args"]
        assert "--disable-blink-features=AutomationControlled" in args
        assert "--window-size=1280,720" in args

        # Verify context args
        mock_browser.new_context.assert_called_once_with(
            user_agent="TestUserAgent/1.0",
            viewport={"width": 1280, "height": 720},
            locale="en-CA",
            timezone_id="America/Toronto",
            permissions=["notifications"],
        )

        # Test new_page
        # We need to mock stealth_async since playwright_stealth might not be installed in test env
        with patch(
            "src.auth.stealth_browser.stealth_async", new_callable=AsyncMock, create=True
        ) as mock_stealth:
            page = await browser.new_page()

            # Verify evasions
            mock_stealth.assert_called_once_with(mock_page)
            mock_page.add_init_script.assert_called_once()

            # Verify script contents
            script = mock_page.add_init_script.call_args.args[0]
            assert "navigator.webdriver" in script
            assert "hardwareConcurrency', { get: () => 8 }" in script
            assert "languages', { get: () => ['en-CA'" in script
            assert "navigator.plugins" in script
            assert "notifications" in script

        # Test close
        await browser.close()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_new_page_without_launch_fails(dummy_fingerprint):
    browser = StealthBrowser(fingerprint=dummy_fingerprint)
    with pytest.raises(RuntimeError):
        await browser.new_page()
