import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from run import main, parse_args


@pytest.fixture
def mock_session_manager():
    with patch("src.auth.session_manager.AuthenticatedSessionManager") as mock:
        instance = mock.return_value
        instance.is_authenticated = True
        instance.initialize = AsyncMock()
        instance.login = AsyncMock()
        instance.close = AsyncMock()
        yield instance


@pytest.fixture
def mock_rate_limiter():
    with patch("run.RateLimiter") as mock:
        instance = mock.return_value
        instance.acquire = AsyncMock()
        yield instance


@pytest.fixture
def mock_init_db():
    with patch("run.init_db") as mock:
        yield mock


@pytest.fixture
def mock_save_run():
    with patch("run.save_run") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_save_target_status():
    with patch("run.save_target_status") as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_save_profile():
    with patch("run.save_profile") as mock:
        yield mock


@pytest.fixture
def mock_read_targets():
    with patch("run.read_targets") as mock:
        mock.return_value = [("https://instagram.com/test", False)]
        yield mock


@pytest.fixture
def mock_get_successful_targets():
    with patch("run.get_successful_targets") as mock:
        mock.return_value = set()
        yield mock


@pytest.fixture
def mock_browser_worker():
    with patch("run.BrowserWorker") as mock:
        instance = mock.return_value
        instance.extract_public_profile = AsyncMock(return_value={"followers": "1.2k"})
        yield instance


@pytest.fixture
def mock_route_authenticated():
    with patch("src.router.route_authenticated") as mock:
        auth_worker = AsyncMock()
        auth_worker.__class__.__name__ = "AuthenticatedWorker"
        auth_worker.extract_profile = AsyncMock(return_value={"id": "u1", "username": "test"})
        auth_worker.extract_posts = AsyncMock(return_value=[])
        mock.return_value = auth_worker
        yield mock


@patch("sys.argv", ["run.py", "--test-login"])
def test_test_login_flag_success(mock_session_manager, capsys):
    """Test the --test-login flag early exit."""
    with pytest.raises(SystemExit) as e:
        import asyncio

        asyncio.run(main())

    assert e.value.code == 0
    mock_session_manager.initialize.assert_called_once()
    mock_session_manager.login.assert_called_once()
    mock_session_manager.close.assert_called_once()


@patch("sys.argv", ["run.py", "--test-login"])
def test_test_login_flag_failure(mock_session_manager, capsys):
    """Test the --test-login flag failure."""
    mock_session_manager.is_authenticated = False

    with pytest.raises(SystemExit) as e:
        import asyncio

        asyncio.run(main())

    assert e.value.code == 1


@patch("sys.argv", ["run.py", "--authenticated", "--dry-run"])
def test_authenticated_run(
    mock_session_manager,
    mock_init_db,
    mock_save_run,
    mock_read_targets,
    mock_rate_limiter,
    mock_get_successful_targets,
    mock_save_target_status,
):
    """Test authenticated session creation and dry-run skips extraction."""
    import asyncio

    asyncio.run(main())

    mock_session_manager.initialize.assert_called_once()
    mock_session_manager.login.assert_called_once()
    mock_session_manager.close.assert_called_once()


@patch("sys.argv", ["run.py", "--authenticated"])
def test_authenticated_run_fallback(
    mock_session_manager,
    mock_init_db,
    mock_save_run,
    mock_read_targets,
    mock_rate_limiter,
    mock_get_successful_targets,
    mock_save_target_status,
    mock_save_profile,
    mock_browser_worker,
):
    """Test fallback when authentication fails during run."""
    mock_session_manager.is_authenticated = False

    import asyncio

    asyncio.run(main())

    mock_session_manager.initialize.assert_called_once()
    mock_session_manager.login.assert_called_once()

    # Browser worker should be used because auth failed
    mock_browser_worker.extract_public_profile.assert_called_once()
    mock_session_manager.close.assert_called_once()


@patch("sys.argv", ["run.py", "--authenticated"])
@patch("src.normalizer.normalize_authenticated_data")
@patch("run.save_profile")
def test_authenticated_extraction(
    mock_save_profile,
    mock_normalize,
    mock_session_manager,
    mock_init_db,
    mock_save_run,
    mock_read_targets,
    mock_rate_limiter,
    mock_get_successful_targets,
    mock_save_target_status,
    mock_route_authenticated,
):
    """Test authenticated profile extraction logic."""
    from datetime import datetime, timezone

    from src.schemas import AuthenticatedProfileSchema

    mock_normalize.return_value = (
        AuthenticatedProfileSchema(
            profile_id="test",
            username="test",
            extracted_at=datetime.now(timezone.utc),
            source="api",
            exact_followers=1000,
            exact_following=100,
            exact_posts_count=10,
        ),
        [],
    )

    import asyncio

    asyncio.run(main())

    # Auth worker methods should be called
    auth_worker = mock_route_authenticated.return_value
    auth_worker.extract_profile.assert_called_once()
    auth_worker.extract_posts.assert_called_once()
    mock_save_profile.assert_called_once()
    mock_session_manager.close.assert_called_once()


@patch("run.save_target_status")
@patch("run.save_profile")
@patch("sys.argv", ["run.py"])
def test_unauthenticated_flow(
    mock_save_profile,
    mock_save_target_status,
    mock_init_db,
    mock_save_run,
    mock_read_targets,
    mock_rate_limiter,
    mock_get_successful_targets,
    mock_browser_worker,
):
    """Test the unauthenticated flow remains intact."""
    import asyncio

    asyncio.run(main())

    # Browser worker should be used
    mock_browser_worker.extract_public_profile.assert_called_once()


@patch("sys.argv", ["run.py", "--test-login"])
def test_session_cleanup_on_error(mock_session_manager):
    """Test session_manager.close() is called on exception."""
    mock_session_manager.login.side_effect = Exception("Crash")

    with pytest.raises(SystemExit):
        import asyncio

        asyncio.run(main())

    mock_session_manager.close.assert_called_once()
