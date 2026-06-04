import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from playwright.async_api import Error as PlaywrightError

from src.auth.exceptions import AccountLockedError, AuthenticationError
from src.auth.session_manager import AuthenticatedSessionManager


@pytest.fixture
def mock_env(monkeypatch):
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", key)
    monkeypatch.setenv("INSTAGRAM_USERNAME", "test_user")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "test_pass")
    return key


@pytest.mark.asyncio
async def test_session_manager_init_no_session(mock_env):
    with (
        patch("src.auth.session_manager.CredentialStore") as MockStore,
        patch("src.auth.session_manager.FingerprintManager") as MockFP,
        patch("src.auth.session_manager.StealthBrowser") as MockBrowser,
    ):

        mock_store = MockStore.return_value
        mock_store.load_session.return_value = None

        mock_fp = MockFP.return_value
        mock_fp.generate.return_value = {"viewport": {"width": 100, "height": 100}}

        mock_browser = MockBrowser.return_value
        mock_context = AsyncMock()
        mock_browser.launch = AsyncMock(return_value=mock_context)

        manager = AuthenticatedSessionManager({})
        result = await manager.initialize()

        # We don't have cookies, so we shouldn't be authenticated yet
        assert result is False
        assert manager.is_authenticated is False
        mock_fp.generate.assert_called_once()
        mock_browser.launch.assert_called_once()


@pytest.mark.asyncio
async def test_session_manager_init_with_session(mock_env):
    with (
        patch("src.auth.session_manager.CredentialStore") as MockStore,
        patch("src.auth.session_manager.FingerprintManager") as MockFP,
        patch("src.auth.session_manager.StealthBrowser") as MockBrowser,
    ):

        mock_store = MockStore.return_value
        mock_store.load_session.return_value = [{"name": "test", "value": "123"}]

        mock_fp = MockFP.return_value
        mock_fp.generate.return_value = {"viewport": {"width": 100, "height": 100}}

        mock_browser = MockBrowser.return_value
        mock_context = AsyncMock()
        mock_browser.launch = AsyncMock(return_value=mock_context)

        manager = AuthenticatedSessionManager({})
        with patch.object(manager, "verify_session", return_value=True):
            result = await manager.initialize()

            # Since verify passed, we should be authenticated
            assert result is True
            assert manager.is_authenticated is True
            mock_context.add_cookies.assert_called_once()


@pytest.mark.asyncio
async def test_session_manager_login_flow(mock_env):
    manager = AuthenticatedSessionManager({})

    # Mock the components directly on the manager since login() assumes initialize() was called
    manager.stealth_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_context.cookies.return_value = [{"name": "sessionid", "value": "123"}]
    manager.stealth_browser.context = mock_context
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock()
    page.url = "https://www.instagram.com/direct/inbox/"

    loc = MagicMock()
    loc_first = MagicMock()
    loc_first.wait_for = AsyncMock()
    loc_first.element_handle = AsyncMock(return_value=AsyncMock())
    loc.first = loc_first
    page.locator.return_value = loc

    manager.stealth_browser.new_page.return_value = page

    with (
        patch.object(manager.mimicry, "random_action_delay", new_callable=AsyncMock) as mock_delay,
        patch.object(manager.mimicry, "move_mouse_human_like", new_callable=AsyncMock) as mock_move,
        patch.object(manager.mimicry, "type_human_like", new_callable=AsyncMock) as mock_type,
        patch.object(manager.mimicry, "click_random_offset", new_callable=AsyncMock) as mock_click,
        patch.object(
            manager, "_handle_suspicious_login", new_callable=AsyncMock
        ) as mock_suspicious,
        patch.object(manager.credential_store, "save_session") as mock_save,
    ):

        result = await manager.login()

        assert result is True
        assert manager.is_authenticated is True

        # Verify the structure of behavior mimicry calls
        assert mock_delay.call_count >= 3
        mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_session_manager_login_playwright_error_recovery(mock_env):
    manager = AuthenticatedSessionManager({})

    # Force a playwright error during new_page
    manager.stealth_browser = AsyncMock()
    manager.stealth_browser.new_page.side_effect = PlaywrightError("Browser crashed")

    with (
        patch.object(manager, "close", new_callable=AsyncMock) as mock_close,
        patch.object(manager, "initialize", new_callable=AsyncMock) as mock_init,
    ):

        result = await manager.login()

        # Login should fail but recover gracefully
        assert result is False
        mock_close.assert_called_once()
        mock_init.assert_called_once()


@pytest.mark.asyncio
async def test_verify_session(mock_env):
    manager = AuthenticatedSessionManager({})
    # No browser
    assert await manager.verify_session() is False

    manager.stealth_browser = AsyncMock()
    # With browser
    assert await manager.verify_session() is True


@pytest.mark.asyncio
async def test_refresh_session(mock_env):
    manager = AuthenticatedSessionManager({})
    with (
        patch.object(manager, "verify_session", new_callable=AsyncMock) as mock_verify,
        patch.object(manager, "login", new_callable=AsyncMock) as mock_login,
    ):

        # Session valid
        mock_verify.return_value = True
        assert await manager.refresh_session() is True
        mock_login.assert_not_called()

        # Session invalid
        mock_verify.return_value = False
        mock_login.return_value = True
        assert await manager.refresh_session() is True
        mock_login.assert_called_once()


def test_switch_to_backup_account(mock_env, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_BACKUP_USERNAME", "backup")
    monkeypatch.setenv("INSTAGRAM_BACKUP_PASSWORD", "backpass")

    manager = AuthenticatedSessionManager({})
    manager.is_authenticated = True

    with patch.object(manager.credential_store, "clear_session") as mock_clear:
        manager.switch_to_backup_account()
        assert manager.username == "backup"
        assert manager.password == "backpass"
        assert manager.is_authenticated is False
        mock_clear.assert_called_once()


@pytest.mark.asyncio
async def test_extract_profile_authenticated(mock_env):
    manager = AuthenticatedSessionManager({})
    with pytest.raises(Exception, match="Cannot extract data: Not authenticated"):
        await manager.extract_profile_authenticated("target")

    manager.is_authenticated = True
    result = await manager.extract_profile_authenticated("target")
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_close_manager(mock_env):
    manager = AuthenticatedSessionManager({})
    manager.is_authenticated = True
    stealth_mock = AsyncMock()
    manager.stealth_browser = stealth_mock

    mock_context = AsyncMock()
    mock_context.cookies.return_value = [{"name": "test", "value": "123"}]
    stealth_mock.context = mock_context

    with patch.object(manager.credential_store, "save_session") as mock_save:
        await manager.close()
        mock_save.assert_called_once()
        stealth_mock.close.assert_called_once()
        assert manager.stealth_browser is None


from unittest import mock


@pytest.mark.asyncio
async def test_handle_suspicious_login_no_prompt(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    loc = MagicMock()
    loc.first = MagicMock()
    loc.first.wait_for = AsyncMock(side_effect=Exception("Timeout"))
    page.locator.return_value = loc

    result = await manager._handle_suspicious_login(page)
    assert result is True


@pytest.mark.asyncio
async def test_handle_suspicious_login_password_change(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    loc = MagicMock()
    loc.first = MagicMock()
    loc.first.wait_for = AsyncMock(return_value=None)
    page.locator.return_value = loc
    page.content = AsyncMock(return_value="Change Your Password")

    pwd_btn = AsyncMock()
    pwd_btn.is_visible.return_value = True
    page.query_selector = AsyncMock(
        side_effect=lambda selector: pwd_btn if "Change Your Password" in selector else None
    )

    with pytest.raises(AuthenticationError, match="Instagram requires password change"):
        await manager._handle_suspicious_login(page)


@pytest.mark.asyncio
async def test_handle_suspicious_login_this_was_me(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    loc = MagicMock()
    loc.first = MagicMock()
    loc.first.wait_for = AsyncMock(return_value=None)
    page.locator.return_value = loc
    page.content = AsyncMock(return_value="We noticed an unusual login attempt")
    page.wait_for_load_state = AsyncMock()

    this_was_me_btn = AsyncMock()

    def qs_side_effect(selector):
        if "This was me" in selector:
            return this_was_me_btn
        return None

    page.query_selector = AsyncMock(side_effect=qs_side_effect)
    manager.mimicry.click_random_offset = AsyncMock()

    result = await manager._handle_suspicious_login(page)
    assert result is True
    manager.mimicry.click_random_offset.assert_called_once_with(this_was_me_btn, mock.ANY)


@pytest.mark.asyncio
async def test_handle_suspicious_login_this_wasnt_me_only(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    loc = MagicMock()
    loc.first = MagicMock()
    loc.first.wait_for = AsyncMock(return_value=None)
    page.locator.return_value = loc
    page.content = AsyncMock(return_value="We noticed an unusual login attempt")

    this_wasnt_me_btn = AsyncMock()

    def qs_side_effect(selector):
        if "This wasn't me" in selector:
            return this_wasnt_me_btn
        return None

    page.query_selector = AsyncMock(side_effect=qs_side_effect)

    with pytest.raises(AuthenticationError, match="Suspicious login detected from unknown device"):
        await manager._handle_suspicious_login(page)


@pytest.mark.asyncio
async def test_handle_suspicious_login_security_code(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    loc = MagicMock()
    loc.first = MagicMock()
    loc.first.wait_for = AsyncMock(return_value=None)
    page.locator.return_value = loc
    page.content = AsyncMock(return_value="Enter the security code we sent")
    page.wait_for_load_state = AsyncMock()

    sec_code_text = AsyncMock()
    sec_code_text.is_visible.return_value = True
    code_input = AsyncMock()
    submit_btn = AsyncMock()

    def qs_side_effect(selector):
        if "Enter the security code we sent" in selector:
            return sec_code_text
        if "security_code" in selector:
            return code_input
        if "Submit" in selector:
            return submit_btn
        return None

    page.query_selector = AsyncMock(side_effect=qs_side_effect)
    manager.mimicry.type_human_like = AsyncMock()
    manager.mimicry.click_random_offset = AsyncMock()

    with patch("asyncio.get_event_loop") as mock_loop:

        async def slow_input(*args):
            return "123456"

        mock_loop.return_value.run_in_executor = slow_input

        result = await manager._handle_suspicious_login(page)
        assert result is True
        manager.mimicry.type_human_like.assert_called_once()
        manager.mimicry.click_random_offset.assert_called_once_with(submit_btn, mock.ANY)


@pytest.mark.asyncio
async def test_check_page_errors_captcha_url(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    page.url = "https://instagram.com/challenge/"
    page.content = AsyncMock(return_value="normal page")

    with pytest.raises(AuthenticationError, match="CAPTCHA challenge detected"):
        await manager._check_page_errors(page)


@pytest.mark.asyncio
async def test_check_page_errors_captcha_text(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    page.url = "https://instagram.com/"
    page.content = AsyncMock(return_value="Help us confirm it's you")

    with pytest.raises(AuthenticationError, match="CAPTCHA challenge detected"):
        await manager._check_page_errors(page)


@pytest.mark.asyncio
async def test_check_page_errors_captcha_iframe(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    page.url = "https://instagram.com/"
    page.content = AsyncMock(return_value="normal")
    frame = MagicMock()
    frame.title = AsyncMock(return_value="recaptcha challenge")
    page.frames = [frame]

    with pytest.raises(AuthenticationError, match="CAPTCHA challenge detected"):
        await manager._check_page_errors(page)


@pytest.mark.asyncio
async def test_check_page_errors_wrong_password(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    page.url = "https://instagram.com/"
    page.content = AsyncMock(return_value="Sorry, your password was incorrect")

    with pytest.raises(AuthenticationError, match="Password incorrect"):
        await manager._check_page_errors(page)


@pytest.mark.asyncio
async def test_check_page_errors_account_locked(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    page.url = "https://instagram.com/"
    page.content = AsyncMock(return_value="Your account has been temporarily locked")

    with pytest.raises(AccountLockedError, match="Account locked"):
        await manager._check_page_errors(page)


@pytest.mark.asyncio
async def test_check_page_errors_rate_limit(mock_env):
    manager = AuthenticatedSessionManager({})
    page = MagicMock()
    page.url = "https://instagram.com/"
    page.content = AsyncMock(return_value="Please wait a few minutes before you try again")

    with pytest.raises(Exception, match="RATE_LIMIT"):
        await manager._check_page_errors(page)


@pytest.mark.asyncio
async def test_login_network_error_retries(mock_env):
    manager = AuthenticatedSessionManager({})
    manager.username = "test"
    manager.password = "test"
    manager.stealth_browser = MagicMock()

    with (
        patch.object(manager, "_login_internal", new_callable=AsyncMock) as mock_internal,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):

        # Fail 3 times, then raise AuthenticationError
        mock_internal.side_effect = PlaywrightError("Timeout")

        with pytest.raises(AuthenticationError, match="Network error after 3 retries"):
            await manager.login()

        assert mock_internal.call_count == 4
        assert mock_sleep.call_count == 3


@pytest.mark.asyncio
async def test_login_browser_crash_recovery(mock_env):
    manager = AuthenticatedSessionManager({})
    manager.username = "test"
    manager.password = "test"
    manager.stealth_browser = MagicMock()

    with (
        patch.object(manager, "_login_internal", new_callable=AsyncMock) as mock_internal,
        patch.object(manager, "close", new_callable=AsyncMock) as mock_close,
        patch.object(manager, "initialize", new_callable=AsyncMock) as mock_init,
    ):

        # First attempt crashes, second succeeds
        mock_internal.side_effect = [PlaywrightError("Target closed"), True]

        result = await manager.login()
        assert result is True
        assert mock_internal.call_count == 2
        mock_close.assert_called_once()
        mock_init.assert_called_once()


@pytest.mark.asyncio
async def test_login_account_locked_backup_switch(mock_env):
    manager = AuthenticatedSessionManager({})
    manager.username = "test"
    manager.password = "test"
    manager.stealth_browser = MagicMock()

    with (
        patch.object(manager, "_login_internal", new_callable=AsyncMock) as mock_internal,
        patch.object(manager, "switch_to_backup_account") as mock_switch,
        patch.object(manager, "close", new_callable=AsyncMock) as mock_close,
        patch.object(manager, "initialize", new_callable=AsyncMock) as mock_init,
    ):

        # First attempt locked, second attempt backup succeeds
        mock_internal.side_effect = [AccountLockedError("Locked"), True]

        result = await manager.login()
        assert result is True
        mock_switch.assert_called_once()
        assert mock_internal.call_count == 2


@pytest.mark.asyncio
async def test_login_rate_limit_retries(mock_env):
    manager = AuthenticatedSessionManager({})
    manager.username = "test"
    manager.password = "test"
    manager.stealth_browser = MagicMock()

    with (
        patch.object(manager, "_login_internal", new_callable=AsyncMock) as mock_internal,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):

        # First 2 attempts rate limited, 3rd succeeds
        mock_internal.side_effect = [Exception("RATE_LIMIT"), Exception("RATE_LIMIT"), True]

        result = await manager.login()
        assert result is True
        assert mock_internal.call_count == 3
        assert mock_sleep.call_count == 2
