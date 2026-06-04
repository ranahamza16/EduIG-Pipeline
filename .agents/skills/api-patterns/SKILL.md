# API Patterns Skill
## REST API Design Principles for EduIG-Pipeline

---

## Overview

This skill provides patterns for building robust HTTP API clients using **httpx** (async) for the EduIG-Pipeline project. It covers authentication, error handling, retries, rate limiting, and testing.

---

## Core Rules (Non-Negotiable)

- **Always use `httpx`** — never `requests` or `urllib`
- **Always use `httpx.AsyncClient`** with explicit timeout
- **Always handle** token expiry, rate limits (429), and server errors
- **Always log** every API call with status, latency, and bytes received
- **Never store** tokens in code — read from environment variables only

---

## Pattern 1: Base API Client

```python
import httpx
import structlog
import os
from typing import Any

logger = structlog.get_logger()

class BaseAPIClient:
    """Base class for all HTTP API clients in EduIG-Pipeline.
    
    Provides: authentication, retry logic, error handling, logging.
    """
    
    BASE_URL = "https://graph.instagram.com"
    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    MAX_CONNECTIONS = 10
    
    def __init__(self) -> None:
        self.token = self._load_token()
        self._client: httpx.AsyncClient | None = None
    
    def _load_token(self) -> str | None:
        """Load OAuth token from environment variable only."""
        token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if not token:
            logger.warning("no_oauth_token", message="INSTAGRAM_ACCESS_TOKEN not set")
        return token
    
    async def __aenter__(self) -> "BaseAPIClient":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_connections=self.MAX_CONNECTIONS),
            headers=self._get_default_headers(),
        )
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
    
    def _get_default_headers(self) -> dict[str, str]:
        """Return default headers for all requests."""
        return {
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "EduIG-Pipeline/1.0 (Academic Research)",
        }
    
    def _get_auth_headers(self) -> dict[str, str]:
        """Return authorization headers with Bearer token."""
        if not self.token:
            raise ValueError("No OAuth token available")
        return {"Authorization": f"Bearer {self.token}"}
```

---

## Pattern 2: Safe GET Request with Retry

```python
import asyncio

async def safe_get(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None = None,
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> dict | None:
    """Make a GET request with exponential backoff retry.
    
    Args:
        client: httpx AsyncClient instance
        url: URL path to request
        params: Query parameters
        max_retries: Maximum retry attempts
        base_delay: Base delay in seconds for backoff
        
    Returns:
        Parsed JSON response, or None on failure.
    """
    for attempt in range(max_retries):
        try:
            start_time = asyncio.get_event_loop().time()
            response = await client.get(url, params=params)
            latency = asyncio.get_event_loop().time() - start_time
            
            logger.info(
                "api_request",
                url=url,
                status=response.status_code,
                latency_ms=round(latency * 1000),
                bytes_received=len(response.content),
            )
            
            # Success
            if response.status_code == 200:
                return response.json()
            
            # Rate limited
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("rate_limited", retry_after=retry_after, attempt=attempt)
                await asyncio.sleep(retry_after)
                continue
            
            # Token expired
            if response.status_code == 401:
                logger.error("token_expired", url=url)
                return None
            
            # Permission denied
            if response.status_code == 403:
                logger.error("permission_denied", url=url)
                return None
            
            # Not found
            if response.status_code == 404:
                logger.warning("not_found", url=url)
                return None
            
            # Server error — retry
            if response.status_code >= 500:
                delay = base_delay * (2 ** attempt)
                logger.warning("server_error", status=response.status_code, retry_in=delay)
                await asyncio.sleep(delay)
                continue
            
            response.raise_for_status()
            
        except httpx.ConnectError as e:
            delay = base_delay * (2 ** attempt)
            logger.warning("connect_error", error=str(e), retry_in=delay, attempt=attempt)
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                
        except httpx.TimeoutException as e:
            delay = base_delay * (2 ** attempt)
            logger.warning("timeout", error=str(e), retry_in=delay, attempt=attempt)
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
    
    logger.error("max_retries_exceeded", url=url, max_retries=max_retries)
    return None
```

---

## Pattern 3: Instagram Graph API Worker

```python
class InstagramAPIWorker(BaseAPIClient):
    """Meta Graph API client for consented Instagram accounts.
    
    Only use when: OAuth token present AND target has consent_status='granted'.
    """
    
    async def get_user_profile(self, user_id: str) -> dict | None:
        """Fetch user profile from Graph API.
        
        Args:
            user_id: Instagram user ID (not username)
            
        Returns:
            Profile data dict, or None on failure.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        fields = "id,username,biography,followers_count,follows_count,media_count"
        return await safe_get(
            self._client,
            f"/{user_id}",
            params={"fields": fields, "access_token": self.token},
        )
    
    async def get_user_media(self, user_id: str, limit: int = 10) -> list[dict]:
        """Fetch recent media for a user.
        
        Args:
            user_id: Instagram user ID
            limit: Max number of posts (1-100)
            
        Returns:
            List of media dicts.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        fields = "id,caption,like_count,comments_count,timestamp,media_type"
        data = await safe_get(
            self._client,
            f"/{user_id}/media",
            params={"fields": fields, "limit": limit, "access_token": self.token},
        )
        
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_media_insights(self, media_id: str) -> dict | None:
        """Fetch insights for a specific post (requires creator account).
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            Insights data, or None if not available.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        metrics = "impressions,reach,engagement"
        return await safe_get(
            self._client,
            f"/{media_id}/insights",
            params={"metric": metrics, "access_token": self.token},
        )
```

---

## Pattern 4: Usage Example

```python
# Correct usage with async context manager
async def extract_consented_profile(user_id: str) -> dict | None:
    async with InstagramAPIWorker() as client:
        profile = await client.get_user_profile(user_id)
        if profile:
            media = await client.get_user_media(user_id, limit=10)
            return {"profile": profile, "media": media}
    return None

# In run.py:
import asyncio
result = asyncio.run(extract_consented_profile("12345678"))
```

---

## Pattern 5: Mocking for Tests

```python
# tests/test_api_worker.py
import pytest
import httpx
import respx  # pip install respx

@pytest.mark.asyncio
async def test_get_user_profile_success():
    """Test successful profile fetch."""
    with respx.mock() as mock:
        mock.get("https://graph.instagram.com/12345").mock(
            return_value=httpx.Response(200, json={
                "id": "12345",
                "username": "testuser",
                "followers_count": 1000,
            })
        )
        
        async with InstagramAPIWorker() as client:
            client.token = "fake_token"
            result = await client.get_user_profile("12345")
        
        assert result["id"] == "12345"
        assert result["followers_count"] == 1000

@pytest.mark.asyncio
async def test_get_user_profile_rate_limited():
    """Test 429 rate limit handling."""
    with respx.mock() as mock:
        mock.get("https://graph.instagram.com/12345").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "1"})
        )
        
        async with InstagramAPIWorker() as client:
            client.token = "fake_token"
            result = await client.get_user_profile("12345")
        
        assert result is None
```

---

## API Error Reference

| Status Code | Meaning | Action |
|-------------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad request | Log error, skip target |
| 401 | Token expired | Refresh token or skip |
| 403 | Permission denied | Log, use browser fallback |
| 404 | Not found | Log, skip target |
| 429 | Rate limited | Wait `Retry-After`, then retry |
| 500-503 | Server error | Exponential backoff, retry 3x |

---

## Instagram Graph API Field Reference

| Field | Description | Requires Consent |
|-------|-------------|-----------------|
| `id` | User ID | No |
| `username` | Username | No |
| `biography` | Bio text | No |
| `followers_count` | Follower count | Yes (creator) |
| `follows_count` | Following count | Yes (creator) |
| `media_count` | Post count | Yes (creator) |
| `like_count` | Post likes | Yes (creator) |
| `comments_count` | Post comments | Yes (creator) |

---

**End of API Patterns Skill**
