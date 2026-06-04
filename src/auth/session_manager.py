"""Authenticated session management logic using Cookie Injection."""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from typing import Any

from playwright.async_api import Error as PlaywrightError

from src.auth.exceptions import AuthenticationError
from src.auth.fingerprint_manager import FingerprintManager
from src.auth.stealth_browser import StealthBrowser
from src.logger import get_logger

logger = get_logger()

COOKIE_FILE = "data/session_cookies.json"

class SessionExpiredError(AuthenticationError):
    pass

class AuthenticatedSessionManager:
    """Core Session Manager for authenticated Instagram scraping using Cookie Injection."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.username = os.getenv("INSTAGRAM_USERNAME", "cookie_session")
        self.is_authenticated = False
        self.stealth_browser: StealthBrowser | None = None
        self.fingerprint_manager: FingerprintManager | None = None

    async def initialize(self) -> bool:
        """Initialize session, loading existing cookies if valid."""
        logger.info("session_manager_init")

        try:
            # 1. Fingerprint Generation
            self.fingerprint_manager = FingerprintManager(self.username)
            fingerprint = self.fingerprint_manager.generate()

            # 2. Stealth Browser Launch
            self.stealth_browser = StealthBrowser(fingerprint, logger=logger)
            context = await self.stealth_browser.launch()

            # 3. Load Cookies and verify
            if not self._has_valid_cookie_file():
                logger.warning("No valid session found. Running cookie extractor...")
                self._run_cookie_extractor()
                if not self._has_valid_cookie_file():
                    raise AuthenticationError("Cookie extractor failed to produce a valid session.")

            await self._inject_session(context)
            
            if await self.verify_session():
                self.is_authenticated = True
                return True
            else:
                logger.warning("Session verification failed. Cookies may have expired.")
                self.is_authenticated = False
                return False

        except PlaywrightError as e:
            logger.error("playwright_initialization_error", error=str(e))
        except Exception as e:
            logger.error("session_manager_init_error", error=str(e))

        return False

    def _has_valid_cookie_file(self) -> bool:
        if not os.path.exists(COOKIE_FILE):
            return False
            
        try:
            with open(COOKIE_FILE, "r") as f:
                data = json.load(f)
                
            # Check expiry
            expires_warning = data.get("expires_warning")
            if expires_warning:
                expires_dt = datetime.fromisoformat(expires_warning.replace("Z", "+00:00"))
                if datetime.utcnow().replace(tzinfo=expires_dt.tzinfo) > expires_dt:
                    logger.warning("Cookie file has expired.")
                    return False
            return True
        except Exception:
            return False

    def _run_cookie_extractor(self) -> None:
        """Launch the cookie extractor script synchronously."""
        logger.info("Launching interactive cookie extractor...")
        script_path = os.path.join(os.path.dirname(__file__), "cookie_extractor.py")
        subprocess.run(["python", script_path], check=True)

    async def _inject_session(self, context: Any) -> None:
        with open(COOKIE_FILE, "r") as f:
            data = json.load(f)

        # Ensure correct cookie types
        for c in data.get("cookies", []):
            if "sameSite" not in c:
                c["sameSite"] = "Lax"
            if "expires" in c and c["expires"] == -1:
                del c["expires"]

        # 1. Inject Cookies
        await context.add_cookies(data.get("cookies", []))
        
        # 2. Inject Local Storage & Session Storage
        page = await self.stealth_browser.new_page()
        # Navigate to instagram.com so we are on the right origin for localstorage
        await page.goto("https://www.instagram.com/", timeout=60000)
        
        ls_data = data.get("localStorage", {})
        ss_data = data.get("sessionStorage", {})
        
        await page.evaluate("""
            (storageData) => {
                window.localStorage.clear();
                window.sessionStorage.clear();
                
                for (const [key, value] of Object.entries(storageData.local)) {
                    window.localStorage.setItem(key, value);
                }
                for (const [key, value] of Object.entries(storageData.session)) {
                    window.sessionStorage.setItem(key, value);
                }
            }
        """, {"local": ls_data, "session": ss_data})
        
        logger.info("session_data_injected")
        await page.close()

    async def verify_session(self) -> bool:
        """Check if the current session is valid by navigating to /accounts/edit/."""
        if not self.stealth_browser:
            return False

        try:
            page = await self.stealth_browser.new_page()
            await page.goto("https://www.instagram.com/accounts/edit/", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            current_url = page.url
            if "/accounts/login/" in current_url:
                raise SessionExpiredError("Session expired. Redirected to login.")
                
            logger.info("session_verified", url=current_url)
            await page.close()
            return True
        except SessionExpiredError:
            raise
        except Exception as e:
            logger.error("session_verification_error", error=str(e))
            return False

    async def extract_profile_authenticated(self, target_username: str) -> dict[str, Any]:
        """Extract exact real-time data using the authenticated session."""
        if not self.is_authenticated:
            raise AuthenticationError("Cannot extract data: Not authenticated")

        logger.info("authenticated_extraction", target=target_username)
        return {}

    async def close(self) -> None:
        """Graceful shutdown."""
        if self.stealth_browser:
            await self.stealth_browser.close()
            self.stealth_browser = None

        logger.info("session_manager_closed")
