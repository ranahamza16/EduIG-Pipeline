import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.config_loader import ConfigSchema, RateLimitConfig
from src.exceptions import CircuitBreakerError, RateLimitExceededError
from src.rate_limiter import RateLimiter


@pytest.fixture
def config():
    """Return a test configuration with small delays."""
    c = ConfigSchema()
    c.rate_limit = RateLimitConfig(
        requests_per_hour=5,
        daily_cap=10,
        base_delay=0.1,  # Short delay for fast tests
        max_retries=3,
        backoff_factor=2.0,
        jitter_min=1.0,
        jitter_max=1.0,  # Remove randomness for predictable math
    )
    return c


@pytest.mark.asyncio
async def test_acquire_base_delay(config):
    """Test that acquire() respects the base delay."""
    limiter = RateLimiter(config)

    start = time.time()
    await limiter.acquire()
    await limiter.acquire()
    duration = time.time() - start

    # Second acquire should wait at least base_delay (0.1s)
    assert duration >= 0.1
    assert limiter.requests_this_hour == 2


@pytest.mark.asyncio
async def test_hourly_rate_limit(config):
    """Test that exceeding hourly limit raises exception."""
    limiter = RateLimiter(config)
    config.rate_limit.base_delay = 0.0  # Speed up test

    for _ in range(5):
        await limiter.acquire()

    with pytest.raises(RateLimitExceededError, match="Hourly cap"):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_daily_rate_limit(config):
    """Test that exceeding daily limit raises exception."""
    limiter = RateLimiter(config)
    config.rate_limit.base_delay = 0.0
    config.rate_limit.requests_per_hour = 20  # Make hourly cap higher than daily

    for _ in range(10):
        await limiter.acquire()

    with pytest.raises(RateLimitExceededError, match="Daily cap"):
        await limiter.acquire()


@pytest.mark.asyncio
@patch("src.rate_limiter.datetime")
async def test_window_resets(mock_datetime, config):
    """Test that changing hours/days resets the counters."""
    # Setup mock to return a specific fixed time initially
    initial_time = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = initial_time
    mock_datetime.side_effect = lambda *args, **kw: datetime.now(*args, **kw)

    limiter = RateLimiter(config)
    config.rate_limit.base_delay = 0.0

    # Use up hourly limit
    for _ in range(5):
        await limiter.acquire()

    assert limiter.requests_this_hour == 5

    # Advance time by 1 hour
    mock_datetime.now.return_value = initial_time + timedelta(hours=1)

    # Should not raise exception because hour changed
    await limiter.acquire()
    assert limiter.requests_this_hour == 1
    assert limiter.requests_today == 6

    # Advance time by 1 day
    mock_datetime.now.return_value = initial_time + timedelta(days=1)
    await limiter.acquire()

    assert limiter.requests_this_hour == 1
    assert limiter.requests_today == 1


@pytest.mark.asyncio
async def test_circuit_breaker(config):
    """Test that max retries trips the circuit breaker."""
    limiter = RateLimiter(config)

    # Max retries is 3
    limiter.record_failure()
    limiter.record_failure()
    limiter.record_failure()

    with pytest.raises(CircuitBreakerError, match="Circuit tripped"):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_record_success_resets_circuit(config):
    """Test that success resets failure count."""
    limiter = RateLimiter(config)

    limiter.record_failure()
    limiter.record_failure()
    assert limiter.consecutive_failures == 2

    limiter.record_success()
    assert limiter.consecutive_failures == 0


@pytest.mark.asyncio
async def test_exponential_backoff(config):
    """Test that failures increase the delay exponentially."""
    limiter = RateLimiter(config)

    start = time.time()

    # First failure
    # backoff = 0.1 * (2.0 ^ 1) = 0.2
    limiter.record_failure()
    await limiter.acquire()
    duration1 = time.time() - start
    assert duration1 >= 0.2

    # Second failure
    # backoff = 0.1 * (2.0 ^ 2) = 0.4
    start = time.time()
    limiter.record_failure()
    await limiter.acquire()
    duration2 = time.time() - start
    assert duration2 >= 0.4


@pytest.mark.asyncio
async def test_429_penalty(config):
    """Test that 429 errors double the backoff."""
    limiter = RateLimiter(config)

    start = time.time()

    # First failure as 429
    # backoff = (0.1 * (2.0 ^ 1)) * 2 = 0.4
    limiter.record_failure(is_429=True)
    await limiter.acquire()
    duration = time.time() - start
    assert duration >= 0.4
