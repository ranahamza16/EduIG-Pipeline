"""Two-Factor Authentication handler."""

import asyncio
import os
from typing import Any

from playwright.async_api import Page

from src.auth.behavior_mimicry import BehaviorMimicry
from src.auth.exceptions import AuthenticationError, TwoFARequiredError
from src.logger import get_logger

logger = get_logger()


class TwoFAHandler:
    """Manages Two-Factor Authentication challenges during login.

    Implements a fallback chain for obtaining codes:
    1. Reads TOTP secrets/backup codes from environment variables.
    2. Prompts the user via stdin (useful for manual intervention).
    3. Times out after 5 minutes if no code is provided.
    """

    def __init__(self) -> None:
        self.totp_secret = os.getenv("INSTAGRAM_TOTP_SECRET")
        raw_backup_codes = os.getenv("INSTAGRAM_BACKUP_CODES", "")
        self.backup_codes = [c.strip() for c in raw_backup_codes.split(",") if c.strip()]
        self.timeout_seconds = 300  # 5 minutes

    async def handle_2fa(
        self, page: Page, mimicry: BehaviorMimicry, session_logger: Any = logger
    ) -> bool:
        """Detect and handle the 2FA prompt.

        Returns:
            True if 2FA was successfully handled or not required.
        """
        # 1. Detect 2FA prompt
        try:
            # We wait up to 30 seconds for the 2FA input to appear
            # or for text indicating 2FA is needed.
            input_selector = 'input[aria-label*="Security code" i], input[name="verificationCode"]'
            text_selector = 'text="Enter Security Code", text="Two-Factor Authentication"'

            # Wait for either to be visible
            await page.locator(f"{input_selector}, {text_selector}").first.wait_for(
                state="visible", timeout=30000
            )
        except Exception:
            # 2FA prompt not found, assume not required or already passed
            return True

        session_logger.info("2FA_REQUIRED")

        # We need the actual input field
        try:
            await page.wait_for_selector(input_selector, state="visible", timeout=10000)
        except Exception:
            session_logger.error("2FA_FAILURE", reason="Prompt text found but input field missing")
            raise AuthenticationError("2FA input field not found")

        # 2. Try Methods
        # Method A: TOTP
        if self.totp_secret:
            code = self._generate_totp()
            if code:
                session_logger.info("2FA_TOTP_ATTEMPT")
                if await self._submit_code(page, mimicry, input_selector, code, session_logger):
                    session_logger.info("2FA_SUCCESS", method="totp")
                    return True
                session_logger.warning("2FA_FAILURE", method="totp", reason="Code rejected")

        # Method B: Backup Codes
        while self.backup_codes:
            code = self.backup_codes.pop(0)
            session_logger.info("2FA_BACKUP_ATTEMPT")
            if await self._submit_code(page, mimicry, input_selector, code, session_logger):
                session_logger.info("2FA_SUCCESS", method="backup")
                return True
            session_logger.warning("2FA_FAILURE", method="backup", reason="Code rejected")

        # Method C: Stdin Prompt
        session_logger.info("2FA_STDIN_PROMPT")
        try:
            code = await self._get_code_from_stdin()
            if code:
                if await self._submit_code(page, mimicry, input_selector, code, session_logger):
                    session_logger.info("2FA_SUCCESS", method="stdin")
                    return True
                session_logger.warning("2FA_FAILURE", method="stdin", reason="Code rejected")
        except asyncio.TimeoutError:
            session_logger.error("2FA_FAILURE", method="stdin", reason="Timeout")
            raise TwoFARequiredError("2FA prompt timed out")

        # If we get here, all methods failed
        raise AuthenticationError("Too many failed 2FA attempts")

    def _generate_totp(self) -> str | None:
        try:
            import pyotp

            if not self.totp_secret:
                return None
            return pyotp.TOTP(self.totp_secret).now()
        except Exception as e:
            logger.warning("totp_generation_failed", error=str(e))
            return None

    async def _get_code_from_stdin(self) -> str | None:
        loop = asyncio.get_event_loop()
        prompt = f"\n*** ACTION REQUIRED ***\nEnter Instagram 2FA code (5-minute timeout): "
        return await asyncio.wait_for(
            loop.run_in_executor(None, input, prompt), timeout=self.timeout_seconds
        )

    async def _submit_code(
        self,
        page: Page,
        mimicry: BehaviorMimicry,
        input_selector: str,
        code: str,
        session_logger: Any,
    ) -> bool:
        """Submit a code and check the result."""
        # Clear field first if needed, though usually it's empty
        await page.fill(input_selector, "")
        await mimicry.type_human_like(page, input_selector, code, session_logger)
        await mimicry.random_action_delay(session_logger)

        # Click confirm button
        btn_selector = 'button:has-text("Confirm"), button[type="submit"]'
        btn = await page.query_selector(btn_selector)
        if btn:
            await mimicry.click_random_offset(btn, session_logger)

        # Wait for either success (checkbox or navigation) or error message
        await mimicry.random_action_delay(session_logger)

        try:
            # Check for error message
            error_selector = (
                'text="Please check the code we sent you and try again", text="invalid"'
            )
            error_el = await page.query_selector(error_selector)
            if error_el and await error_el.is_visible():
                return False

            # Handle "Trust this browser" checkbox
            trust_checkbox = 'input[type="checkbox"], label:has-text("Trust this browser")'
            checkbox = await page.query_selector(trust_checkbox)
            if checkbox and await checkbox.is_visible():
                is_checked = await page.evaluate("(el) => el.checked", checkbox)
                if not is_checked:
                    await mimicry.click_random_offset(checkbox, session_logger)
                    session_logger.info("trust_browser_checked")

            return True
        except Exception as e:
            session_logger.warning("submit_code_validation_error", error=str(e))
            # Assume success if we didn't explicitly see an error and we navigated away
            return True
