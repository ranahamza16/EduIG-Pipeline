"""Playwright browser worker for Instagram public data extraction.

Uses headless Chromium to navigate to public profiles and extract
metadata using JSON injection and CSS fallback strategies.
"""

from typing import Any

import structlog
from playwright.async_api import Page, async_playwright

from src.config_loader import ConfigSchema

logger = structlog.get_logger(__name__)
audit = structlog.get_logger("audit")


class BrowserWorker:
    """Worker for extracting public Instagram data via Playwright."""

    def __init__(self, config: ConfigSchema, logger_instance: Any = None):
        """Initialize the browser worker.

        Args:
            config: Application configuration.
            logger_instance: Optional bound logger for context.
        """
        self.config = config
        self.logger = logger_instance or logger

    async def extract_public_profile(self, username: str) -> dict[str, Any]:
        """Extract public Instagram profile using Playwright.

        Args:
            username: Instagram username (without @).

        Returns:
            Raw profile data dict. Empty dict on failure.
        """
        self.logger.info("browser_worker_started", target=username)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.browser.headless)
            try:
                context = await browser.new_context(
                    viewport={
                        "width": self.config.browser.viewport_width,
                        "height": self.config.browser.viewport_height,
                    }
                )
                page = await context.new_page()

                # Navigate with human-like delay
                target_url = f"https://www.instagram.com/{username}/"
                self.logger.debug("navigating", url=target_url)

                # We catch timeout errors gracefully
                try:
                    await page.goto(target_url, timeout=self.config.browser.timeout)
                except Exception as e:
                    if "Timeout" in str(e):
                        self.logger.error("navigation_timeout", target=username)
                        return {}
                    raise e

                await page.wait_for_timeout(3000)  # Human-like delay

                # Strategy 1: JSON extraction from page scripts (PRIMARY)
                data = await page.evaluate("""
                    () => {
                        const sel = 'script[type="application/json"]';
                        const scripts = document.querySelectorAll(sel);
                        for (const script of scripts) {
                            try {
                                const json = JSON.parse(script.textContent);
                                const str = script.textContent;
                                if (str.includes("edge_followed_by") || str.includes("followers_count") || str.includes("xdt_api__v1__users__web_profile_info")) {
                                    return json;
                                }
                            } catch(e) {}
                        }
                        return null;
                    }
                """)

                if data:
                    self.logger.info("profile_extracted", target=username, strategy="json")
                    audit.info(
                        "profile_extracted", target=username, strategy="json", source="browser"
                    )

                    self.logger.info("extracting_recent_posts", target=username)
                    recent_posts = self.extract_recent_posts(username, data)
                    data["recent_posts"] = recent_posts

                    return data  # type: ignore[no-any-return]

                # Strategy 2: CSS selector fallback
                self.logger.info("json_extraction_failed_trying_fallback", target=username)
                fallback_data = await self._fallback_dom_extraction(page, username)

                self.logger.info("profile_extracted", target=username, strategy="dom_fallback")
                audit.info(
                    "profile_extracted", target=username, strategy="dom_fallback", source="browser"
                )

                # Try to extract posts while we are still here
                self.logger.info("extracting_recent_posts", target=username)
                recent_posts = self.extract_recent_posts(username, fallback_data)
                fallback_data["recent_posts"] = recent_posts

                return fallback_data

            except Exception as e:
                self.logger.error("extraction_failed", target=username, error=str(e))
                return {}
            finally:
                await browser.close()

    async def _fallback_dom_extraction(self, page: Page, username: str) -> dict[str, Any]:
        """CSS selector fallback when JSON extraction fails.

        Note: Instagram's DOM changes frequently. This is a best-effort extraction.

        Args:
            page: Playwright Page instance.
            username: Target username.

        Returns:
            Dictionary of extracted fields.
        """
        meta_desc = await page.query_selector("meta[name='description']")
        meta_content = await meta_desc.get_attribute("content") if meta_desc else ""

        return {
            "username": username,
            "followers": meta_content,
            "bio": await self._safe_text(
                page, "div.-vDIg span"
            ),  # Common class for bio, though fragile
            "raw_title": await page.title(),
        }

    async def _safe_text(self, page: Page, selector: str) -> str | None:
        """Safely extract text from a CSS selector.

        Args:
            page: Playwright Page instance.
            selector: CSS selector to query.

        Returns:
            Inner text of the element, or None if not found/error.
        """
        try:
            element = await page.query_selector(selector)
            return await element.inner_text() if element else None
        except Exception:
            return None

    def extract_recent_posts(self, username: str, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract recent posts from the raw GraphQL profile data.

        Note: Instagram severely limits pagination on public endpoints.
        We can reliably extract the first 12 posts from the initial page load,
        but we will cap it at 10 to meet the requirement.

        Args:
            username: Target username.
            raw_data: The raw profile JSON data extracted via Playwright.

        Returns:
            List of raw post dictionaries.
        """
        posts = []

        try:
            # Navigate the JSON structure to find the timeline media edges
            # Structure: graphql -> user -> edge_owner_to_timeline_media -> edges
            user_data = raw_data.get("graphql", {}).get("user", {})
            if not user_data:
                # If graphql format is missing, try alternative JSON structures
                user_data = raw_data.get("data", {}).get("user", {})

            edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])

            for edge in edges[:10]:  # Limit to 10 as requested
                node = edge.get("node", {})
                if not node:
                    continue

                post_data = {
                    "id": node.get("id"),
                    "shortcode": node.get("shortcode"),
                    "__typename": node.get("__typename"),
                    "edge_media_preview_like": node.get("edge_media_preview_like"),
                    "edge_media_to_comment": node.get("edge_media_to_comment"),
                    "taken_at_timestamp": node.get("taken_at_timestamp"),
                    "edge_media_to_caption": node.get("edge_media_to_caption"),
                }
                posts.append(post_data)

        except Exception as e:
            self.logger.error("post_extraction_failed", target=username, error=str(e))

        return posts

    async def extract_post(self, shortcode: str) -> dict[str, Any]:
        """Extract a single public Instagram post using Playwright.

        Args:
            shortcode: Instagram post shortcode (e.g. CbXYZ123).

        Returns:
            Raw post data dict. Empty dict on failure.
        """
        self.logger.info("browser_worker_post_started", target=shortcode)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.browser.headless)
            try:
                context = await browser.new_context(
                    viewport={
                        "width": self.config.browser.viewport_width,
                        "height": self.config.browser.viewport_height,
                    }
                )
                page = await context.new_page()

                target_url = f"https://www.instagram.com/p/{shortcode}/"
                self.logger.debug("navigating", url=target_url)

                try:
                    await page.goto(target_url, timeout=self.config.browser.timeout)
                except Exception as e:
                    if "Timeout" in str(e):
                        self.logger.error("navigation_timeout", target=shortcode)
                        return {}
                    raise e

                await page.wait_for_timeout(3000)

                data = await page.evaluate("""
                    () => {
                        const sel = 'script[type="application/json"]';
                        const scripts = document.querySelectorAll(sel);
                        for (const script of scripts) {
                            try {
                                const json = JSON.parse(script.textContent);
                                if (json?.require) return json;
                            } catch(e) {}
                        }
                        return null;
                    }
                """)

                if data:
                    self.logger.info("post_extracted", target=shortcode, strategy="json")
                    audit.info(
                        "post_extracted", target=shortcode, strategy="json", source="browser"
                    )
                    from typing import cast

                    return cast(dict[str, Any], data)

                self.logger.warning("json_extraction_failed_for_post", target=shortcode)
                return {}

            except Exception as e:
                self.logger.error("extraction_failed", target=shortcode, error=str(e))
                return {}
            finally:
                await browser.close()
