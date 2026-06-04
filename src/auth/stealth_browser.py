"""Stealth browser context implementation for anti-detection."""

from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

try:
    from playwright_stealth import Stealth  # type: ignore
except ImportError:
    # We will handle missing playwright-stealth gracefully, but it's expected to be installed
    pass

from src.auth.behavior_mimicry import BehaviorMimicry
from src.logger import get_logger

# Default logger
default_logger = get_logger()


class StealthBrowser:
    """Manages an anti-detection browser session using Playwright and CDP overrides."""

    def __init__(self, fingerprint: dict[str, Any], logger: Any = default_logger) -> None:
        self.fingerprint = fingerprint
        self.logger = logger
        self.mimicry = BehaviorMimicry()
        self._playwright: Any = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None

    def get_fingerprint(self) -> dict[str, Any]:
        """Return the active fingerprint dictionary."""
        return self.fingerprint

    async def launch(self, headless: bool = True) -> BrowserContext:
        """Launch the stealth browser with fingerprint configuration."""
        self.logger.info("launching_stealth_browser", headless=headless)
        self._playwright = await async_playwright().start()

        viewport = self.fingerprint["viewport"]
        window_size = f"{viewport['width']},{viewport['height']}"

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            f"--window-size={window_size}",
        ]

        self.browser = await self._playwright.chromium.launch(headless=headless, args=args)

        self.context = await self.browser.new_context(
            user_agent=self.fingerprint["user_agent"],
            viewport=viewport,
            locale=self.fingerprint["locale"],
            timezone_id=self.fingerprint["timezone_id"],
            permissions=["notifications"],  # We'll override the behavior via CDP
        )

        # Apply stealth at the context level if supported, otherwise handled per page
        self.logger.info("stealth_browser_launched")
        return self.context

    async def new_page(self) -> Page:
        """Create a new page with all stealth evasions fully applied."""
        if not self.context:
            raise RuntimeError("Browser context not launched. Call launch() first.")

        page = await self.context.new_page()

        # 1. Baseline evasions from playwright-stealth
        try:
            await Stealth().apply_stealth_async(page)
        except NameError:
            self.logger.warning(
                "playwright_stealth_missing", message="playwright-stealth not installed"
            )

        # 2. Manual CDP Overrides via init scripts
        locale = self.fingerprint["locale"]
        hardware_concurrency = self.fingerprint.get("hardware_concurrency", 4)

        override_script = f"""
        // navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        
        // navigator.hardwareConcurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hardware_concurrency} }});
        
        // navigator.languages
        Object.defineProperty(navigator, 'languages', {{ get: () => ['{locale}', 'en-US', 'en'] }});
        
        // navigator.plugins (fake plugins)
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                {{ name: 'Chrome PDF Viewer', filename: 'mhjimiapjmagpiencosiggoagpcfdfal', description: '' }},
                {{ name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }}
            ]
        }});
        
        // window.chrome
        window.chrome = {{
            runtime: {{}}
        }};
        
        // Permissions API Override for notifications
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = parameters => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission === 'default' ? 'prompt' : Notification.permission }}) :
                originalQuery(parameters)
        );
        """

        await page.add_init_script(override_script)

        self.logger.debug("stealth_evasions_applied_to_page")
        return page

    async def close(self) -> None:
        """Cleanup browser resources."""
        self.logger.info("closing_stealth_browser")
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
