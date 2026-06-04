import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth.authenticated_worker import AuthenticatedWorker
from src.auth.exceptions import AuthenticationError
from src.schemas import AuthenticatedProfileSchema, PostSchema


@pytest.fixture
def mock_session_manager():
    sm = MagicMock()
    sm.is_authenticated = True
    sm.stealth_browser = MagicMock()

    # Mock playwright context
    context = AsyncMock()
    context.cookies = AsyncMock(
        return_value=[
            {"name": "csrftoken", "value": "mock_csrf"},
            {"name": "sessionid", "value": "mock_session"},
        ]
    )
    sm.stealth_browser.context = context

    return sm


@pytest.fixture
def rest_fixture():
    with open("tests/fixtures/instagram_rest_profile.json") as f:
        return json.load(f)


@pytest.fixture
def graphql_fixture():
    with open("tests/fixtures/instagram_graphql_profile.json") as f:
        return json.load(f)


@pytest.fixture
def worker(mock_session_manager):
    return AuthenticatedWorker(mock_session_manager, {"timeout": 10}, None)


@pytest.mark.asyncio
async def test_extract_profile_success(worker, rest_fixture):
    """Test extract_profile returns correct exact counts."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = rest_fixture
        mock_get.return_value = mock_resp

        profile = await worker.extract_profile("test_user")

        assert isinstance(profile, AuthenticatedProfileSchema)
        assert profile.exact_followers == 1247
        assert profile.exact_following == 456
        assert profile.exact_posts_count == 89
        assert profile.bio == "Test biography"
        assert profile.profile_picture_url == "https://example.com/pic_hd.jpg"


@pytest.mark.asyncio
async def test_extract_posts_success(worker, rest_fixture):
    """Test extract_posts returns posts with correct ER and details."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = rest_fixture
        mock_get.return_value = mock_resp

        posts = await worker.extract_posts("test_user", limit=3)

        assert len(posts) == 3
        # Post 1
        assert posts[0].likes == 234
        assert posts[0].comments == 12
        assert posts[0].engagement_rate == (234 + 12) / 1247
        assert posts[0].caption == "Post 1 caption #test"

        # Post 2
        assert posts[1].likes == 100
        assert posts[1].comments == 5
        assert posts[1].engagement_rate == (100 + 5) / 1247

        # Post 3
        assert posts[2].likes == 50
        assert posts[2].comments == 2
        assert posts[2].engagement_rate == (50 + 2) / 1247


@pytest.mark.asyncio
async def test_graphql_pagination(worker, rest_fixture, graphql_fixture):
    """Test extract_posts loops using GraphQL when limit > REST edges."""
    with patch("httpx.AsyncClient.get") as mock_get:
        # First call is REST, second is GraphQL
        rest_resp = MagicMock()
        rest_resp.status_code = 200
        rest_resp.json.return_value = rest_fixture

        gql_resp = MagicMock()
        gql_resp.status_code = 200
        gql_resp.json.return_value = graphql_fixture

        mock_get.side_effect = [
            rest_resp,
            rest_resp,
            gql_resp,
        ]  # First REST is inside extract_profile() call, second inside extract_posts, third GraphQL

        # We need 5 posts, REST has 3, GraphQL has 2
        with patch("asyncio.sleep", AsyncMock()):  # skip sleep
            posts = await worker.extract_posts("test_user", limit=5)

        assert len(posts) == 5
        assert posts[0].likes == 234
        assert posts[3].likes == 20
        assert posts[4].likes == 30


@pytest.mark.asyncio
async def test_http_429_rate_limit(worker, rest_fixture):
    """Test rate limit header parsing and backoff."""
    with patch("httpx.AsyncClient.get") as mock_get:
        limit_resp = MagicMock()
        limit_resp.status_code = 429
        limit_resp.headers = {"retry-after": "1"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = rest_fixture

        mock_get.side_effect = [limit_resp, success_resp]

        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            profile = await worker.extract_profile("test_user")

            assert profile.exact_followers == 1247
            mock_sleep.assert_called_once_with(1)
            assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_http_429_rate_limit_exceeded(worker):
    """Test failure after 3 retries on 429."""
    with patch("httpx.AsyncClient.get") as mock_get:
        limit_resp = MagicMock()
        limit_resp.status_code = 429
        limit_resp.headers = {"retry-after": "0"}

        mock_get.return_value = limit_resp

        with patch("asyncio.sleep", AsyncMock()):
            with pytest.raises(AuthenticationError, match="Rate limit exceeded"):
                await worker.extract_profile("test_user")


@pytest.mark.asyncio
async def test_invalid_json_handling(worker):
    """Test handling of invalid JSON responses."""
    with patch("httpx.AsyncClient.get") as mock_get:
        invalid_resp = MagicMock()
        invalid_resp.status_code = 200
        import json

        invalid_resp.json.side_effect = json.JSONDecodeError("error", "doc", 0)

        mock_get.return_value = invalid_resp

        with pytest.raises(ValueError, match="Failed to parse JSON response"):
            await worker.extract_profile("test_user")


def test_fallback_unauthenticated():
    """Test route_authenticated fallback behavior when session lacks auth."""
    from src.router import route_authenticated

    sm = MagicMock()
    sm.is_authenticated = False

    worker = route_authenticated(sm, {})
    assert worker.__class__.__name__ == "BrowserWorker"


def test_fallback_unauthenticated_stealth_missing():
    """Test behavior if stealth browser is not instantiated."""
    sm = MagicMock()
    sm.is_authenticated = True
    sm.stealth_browser = None

    worker = AuthenticatedWorker(sm, {})
    import pytest

    with pytest.raises(AuthenticationError, match="browser context is missing"):
        import asyncio

        asyncio.run(worker._get_headers_and_cookies())


def test_parse_exact_count(worker):
    """Test parsing of formatted string numbers."""
    assert worker._parse_exact_count(None) == 0
    assert worker._parse_exact_count(123) == 123
    assert worker._parse_exact_count("456") == 456
    assert worker._parse_exact_count("1.2k") == 1200
    assert worker._parse_exact_count("1.5M") == 1500000
    assert worker._parse_exact_count("1,234") == 1234
    assert worker._parse_exact_count("invalid") == 0
