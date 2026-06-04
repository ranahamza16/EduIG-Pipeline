"""Tests for the TwoFAHandler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import Page

from src.auth.behavior_mimicry import BehaviorMimicry
from src.auth.exceptions import AuthenticationError, TwoFARequiredError
from src.auth.two_fa_handler import TwoFAHandler


@pytest.fixture
def mimicry():
    m = MagicMock(spec=BehaviorMimicry)
    m.type_human_like = AsyncMock()
    m.random_action_delay = AsyncMock()
    m.click_random_offset = AsyncMock()
    return m


@pytest.fixture
def page():
    p = AsyncMock(spec=Page)
    p.locator = MagicMock()
    loc = AsyncMock()
    loc.wait_for = AsyncMock()
    p.locator.return_value.first = loc
    p.wait_for_selector = AsyncMock()
    p.query_selector = AsyncMock()
    p.fill = AsyncMock()
    p.evaluate = AsyncMock(return_value=False)
    return p


@pytest.fixture
def session_logger():
    return MagicMock()


@pytest.mark.asyncio
async def test_no_2fa_prompt(page, mimicry, session_logger):
    handler = TwoFAHandler()
    page.locator.return_value.first.wait_for.side_effect = Exception("Timeout")
    result = await handler.handle_2fa(page, mimicry, session_logger)
    assert result is True


@pytest.mark.asyncio
async def test_totp_success(page, mimicry, session_logger):
    handler = TwoFAHandler()
    handler.totp_secret = "DUMMYSECRET"

    with patch("pyotp.TOTP") as mock_totp:
        mock_totp.return_value.now.return_value = "123456"
        page.query_selector.return_value = None  # No error message

        result = await handler.handle_2fa(page, mimicry, session_logger)
        assert result is True
        session_logger.info.assert_any_call("2FA_SUCCESS", method="totp")


@pytest.mark.asyncio
async def test_totp_fail_then_backup_success(page, mimicry, session_logger):
    handler = TwoFAHandler()
    handler.totp_secret = "DUMMYSECRET"
    handler.backup_codes = ["backup1", "backup2"]

    with patch("pyotp.TOTP") as mock_totp:
        mock_totp.return_value.now.return_value = "123456"

        # First submit returns error, second submit succeeds
        error_el = AsyncMock()
        error_el.is_visible.side_effect = [True, False]

        async def qs_side_effect(selector):
            if "invalid" in selector:
                if error_el.is_visible.call_count == 0:
                    return error_el
                return None
            return None

        page.query_selector.side_effect = qs_side_effect

        result = await handler.handle_2fa(page, mimicry, session_logger)
        assert result is True
        assert len(handler.backup_codes) == 1
        session_logger.info.assert_any_call("2FA_SUCCESS", method="backup")


@pytest.mark.asyncio
async def test_stdin_timeout(page, mimicry, session_logger):
    handler = TwoFAHandler()
    handler.totp_secret = None
    handler.backup_codes = []
    handler.timeout_seconds = 0.01

    with patch("asyncio.get_event_loop") as mock_loop:

        async def slow_input(*args):
            await asyncio.sleep(0.1)

        mock_loop.return_value.run_in_executor = slow_input

        with pytest.raises(TwoFARequiredError):
            await handler.handle_2fa(page, mimicry, session_logger)


@pytest.mark.asyncio
async def test_trust_browser_checkbox(page, mimicry, session_logger):
    handler = TwoFAHandler()
    handler.totp_secret = "SECRET"

    with patch("pyotp.TOTP") as mock_totp:
        mock_totp.return_value.now.return_value = "123456"

        checkbox_mock = AsyncMock()
        checkbox_mock.is_visible.return_value = True

        # Let query_selector return None for error message, and checkbox for trust
        async def qs_side_effect(selector):
            if "invalid" in selector:
                return None
            return checkbox_mock

        page.query_selector.side_effect = qs_side_effect
        page.evaluate.return_value = False  # Not checked

        result = await handler.handle_2fa(page, mimicry, session_logger)
        assert result is True
        mimicry.click_random_offset.assert_called_with(checkbox_mock, session_logger)
        session_logger.info.assert_any_call("trust_browser_checked")


@pytest.mark.asyncio
async def test_too_many_attempts(page, mimicry, session_logger):
    handler = TwoFAHandler()
    handler.totp_secret = "DUMMYSECRET"
    handler.backup_codes = ["fail1"]

    with (
        patch("pyotp.TOTP") as mock_totp,
        patch.object(handler, "_get_code_from_stdin", return_value="stdin_code"),
    ):
        mock_totp.return_value.now.return_value = "123456"

        # Always return error element
        error_el = AsyncMock()
        error_el.is_visible.return_value = True
        page.query_selector.return_value = error_el

        with pytest.raises(AuthenticationError):
            await handler.handle_2fa(page, mimicry, session_logger)
