"""Rate Limiter and Circuit Breaker for EduIG-Pipeline.

Protects against IP bans and rate limits by enforcing global caps,
exponential backoff, and circuit breaking.
"""

import random
import time
from datetime import datetime, timezone

import structlog

from src.config_loader import ConfigSchema
from src.exceptions import CircuitBreakerError, RateLimitExceededError

logger = structlog.get_logger(__name__)
audit = structlog.get_logger("audit")


class RateLimiter:
    """Enforces request limits and circuit breaker patterns."""

    def __init__(self, config: ConfigSchema):
        """Initialize the rate limiter.

        Args:
            config: Application configuration.
        """
        self.config = config.rate_limit

        # State counters
        self.requests_this_hour = 0
        self.requests_today = 0
        self.consecutive_failures = 0

        # Timing trackers
        self.current_hour = datetime.now(timezone.utc).hour
        self.current_day = datetime.now(timezone.utc).date()

        # Next allowed request time
        self._next_allowed_time: float = 0.0

    def _check_and_reset_windows(self) -> None:
        """Reset hourly and daily counters if the window has passed."""
        now = datetime.now(timezone.utc)

        if now.date() > self.current_day:
            self.requests_today = 0
            self.requests_this_hour = 0
            self.current_day = now.date()
            self.current_hour = now.hour
            logger.debug("daily_rate_limit_reset")
        elif now.hour != self.current_hour:
            self.requests_this_hour = 0
            self.current_hour = now.hour
            logger.debug("hourly_rate_limit_reset")

    async def acquire(self) -> None:
        """Wait if necessary before allowing a request to proceed.

        Raises:
            CircuitBreakerError: If the circuit is open (too many failures).
            RateLimitExceededError: If the hourly or daily cap is hit.
        """
        # Check circuit breaker
        if self.consecutive_failures >= self.config.max_retries:
            logger.error("circuit_breaker_tripped", failures=self.consecutive_failures)
            raise CircuitBreakerError(
                f"Circuit tripped after {self.consecutive_failures} failures."
            )

        # Check rolling windows
        self._check_and_reset_windows()

        if self.requests_today >= self.config.daily_cap:
            logger.warning("daily_cap_reached", limit=self.config.daily_cap)
            raise RateLimitExceededError(f"Daily cap of {self.config.daily_cap} reached.")

        if self.requests_this_hour >= self.config.requests_per_hour:
            logger.warning("hourly_cap_reached", limit=self.config.requests_per_hour)
            raise RateLimitExceededError(f"Hourly cap of {self.config.requests_per_hour} reached.")

        # Sleep if we need to back off or enforce base delay
        import asyncio

        now = time.time()
        if now < self._next_allowed_time:
            sleep_time = self._next_allowed_time - now
            logger.debug("rate_limiter_sleeping", sleep_time=round(sleep_time, 2))
            await asyncio.sleep(sleep_time)

        # Update counters
        self.requests_this_hour += 1
        self.requests_today += 1

        # Enforce base delay for the NEXT request
        self._next_allowed_time = time.time() + self.config.base_delay

        logger.debug(
            "request_acquired",
            hourly_count=self.requests_this_hour,
            daily_count=self.requests_today,
        )

    def record_success(self) -> None:
        """Record a successful request and close the circuit."""
        if self.consecutive_failures > 0:
            logger.info("circuit_breaker_reset", previous_failures=self.consecutive_failures)
        self.consecutive_failures = 0

    def record_failure(self, is_429: bool = False) -> None:
        """Record a failed request and calculate exponential backoff.

        Args:
            is_429: Whether the failure was specifically a Rate Limit (429) error.
        """
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.config.max_retries:
            # We don't raise here, we let the NEXT acquire() call raise,
            # but we log it heavily.
            logger.error(
                "max_retries_exceeded",
                failures=self.consecutive_failures,
                limit=self.config.max_retries,
            )
            audit.error("pipeline_tripped", failures=self.consecutive_failures)
            return

        # Calculate backoff: base_delay * (factor ^ failures)
        backoff_base = self.config.base_delay * (
            self.config.backoff_factor**self.consecutive_failures
        )

        # Apply jitter
        jitter = random.uniform(self.config.jitter_min, self.config.jitter_max)
        backoff_delay = backoff_base * jitter

        # If it's a hard 429, penalize harder
        if is_429:
            backoff_delay *= 2

        # Set next allowed time
        self._next_allowed_time = time.time() + backoff_delay

        logger.warning(
            "request_failed_backing_off",
            failures=self.consecutive_failures,
            delay=round(backoff_delay, 2),
            is_429=is_429,
        )
