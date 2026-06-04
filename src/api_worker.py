"""Instagram Graph API worker.

Extracts data for consented profiles using the official Instagram Graph API.
Uses httpx AsyncClient for requests but provides a synchronous interface
for compatibility with the main orchestration loop.
"""

import asyncio
from typing import Any, cast

import httpx
import structlog

from src.config_loader import ConfigSchema
from src.exceptions import RateLimitExceededError


class APIWorker:
    """Worker for extracting consented Instagram data via Graph API."""

    def __init__(self, config: ConfigSchema, logger_instance: Any = None):
        """Initialize the API worker.

        Args:
            config: Application configuration.
            logger_instance: Optional bound logger for context.
        """
        self.config = config
        self.logger = logger_instance or structlog.get_logger(__name__)
        self.audit = structlog.get_logger("audit")

        # We assume the config has the access token if we reached here
        self.token = self.config.api.access_token

    def _get_headers(self) -> dict[str, str]:
        """Get standard HTTP headers for Graph API."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _async_extract_public_profile(self, username: str) -> dict[str, Any]:
        """Asynchronously extract profile using Graph API."""
        self.logger.info("api_worker_started", target=username)

        # First, we need to resolve the Instagram user ID from the username
        # The Graph API requires the IG User ID, not the username, for most endpoints.
        # A common pattern is searching for the user, or if we already have the ID,
        # using it directly.
        # For this pipeline, let's assume `username` is actually the Instagram User ID or we use
        # Business Discovery.
        # Note: Business Discovery is the standard way to get info about an arbitrary user via API.
        # Assuming our access token is attached to an IG Professional account.

        # We will use the Business Discovery endpoint:
        # GET /{our_ig_user_id}?fields=business_discovery.username({username}){username,...}

        # Since we don't have our own IG user ID stored, we simulate standard Graph API node fetch.
        # In a real scenario, you'd configure the base IG User ID.
        # Let's hit a simulated standard endpoint structure:
        url = f"{self.config.api.base_url}/{username}"
        params = {"fields": "username,biography,followers_count,follows_count,media_count"}

        async with httpx.AsyncClient(timeout=self.config.api.timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers(), params=params)

                # Check for rate limit headers
                usage = response.headers.get("x-app-usage", "")
                if usage:
                    self.logger.debug("api_usage_reported", usage=usage)

                response.raise_for_status()
                data = response.json()

                self.logger.info("profile_extracted", target=username, strategy="graph_api")
                self.audit.info(
                    "profile_extracted", target=username, strategy="graph_api", source="api"
                )

                if isinstance(data, dict):
                    return cast(dict[str, Any], data)
                return {}

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 401:
                    self.logger.error("api_token_expired", error=str(e))
                    self._refresh_token()
                elif status_code == 403:
                    self.logger.error("api_permission_denied", target=username)
                elif status_code == 429:
                    self.logger.error("api_rate_limit_exceeded")
                    raise RateLimitExceededError("Graph API rate limit exceeded (429)")
                else:
                    self.logger.error("api_http_error", target=username, status=status_code)
                return {}
            except Exception as e:
                self.logger.error("api_extraction_failed", target=username, error=str(e))
                return {}

    async def _async_extract_recent_posts(self, username: str) -> list[dict[str, Any]]:
        """Asynchronously extract recent posts via Graph API."""
        url = f"{self.config.api.base_url}/{username}/media"
        params: dict[str, str | int] = {
            "fields": "id,shortcode,media_type,like_count,comments_count,timestamp,caption",
            "limit": 10,
        }

        async with httpx.AsyncClient(timeout=self.config.api.timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, dict):
                    return cast(list[dict[str, Any]], data.get("data", []))
                return []

            except Exception as e:
                self.logger.error("api_post_extraction_failed", target=username, error=str(e))
                return []

    def extract_public_profile(self, username: str) -> dict[str, Any]:
        """Synchronous wrapper for profile extraction."""
        data = asyncio.run(self._async_extract_public_profile(username))

        # We simulate extraction of recent posts here as well so the router sees them
        if data:
            recent_posts = self.extract_recent_posts(username)
            data["recent_posts"] = recent_posts

        return data

    def extract_recent_posts(self, username: str) -> list[dict[str, Any]]:
        """Synchronous wrapper for post extraction."""
        return asyncio.run(self._async_extract_recent_posts(username))

    def _refresh_token(self) -> None:
        """Handle OAuth 2.0 token refresh logic.

        In production, this would make a request to the oauth/access_token
        endpoint using the long-lived token secret to get a new token,
        and update the configuration or environment dynamically.
        """
        self.logger.warning("token_refresh_triggered")
        self.audit.warning("token_refresh_triggered", action="refresh_oauth_token")
        # Placeholder for actual refresh logic
