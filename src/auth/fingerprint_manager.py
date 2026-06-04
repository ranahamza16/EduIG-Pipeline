"""Browser fingerprint generation and consistency management."""

import hashlib
import json
import random
from typing import Any

from src.logger import get_logger

logger = get_logger()

# Common modern User-Agents to select from
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]

# Common locales
LOCALES = ["en-US", "en-GB", "en-CA"]

# Common timezones matching the locales
TIMEZONES = {
    "en-US": ["America/New_York", "America/Chicago", "America/Los_Angeles"],
    "en-GB": ["Europe/London"],
    "en-CA": ["America/Toronto", "America/Vancouver"],
}


class FingerprintManager:
    """Manages browser fingerprint consistency per session."""

    def __init__(self, username: str) -> None:
        self.username = username
        self.fingerprint: dict[str, Any] | None = None

    def _generate_deterministic_seed(self) -> int:
        """Generate a stable seed based on the username to keep fingerprints consistent across restarts."""
        hash_digest = hashlib.sha256(self.username.encode()).hexdigest()
        return int(hash_digest[:8], 16)

    def generate(self, force_new: bool = False) -> dict[str, Any]:
        """Generate a consistent fingerprint for the session.

        If force_new is False, this is pseudo-deterministic based on the username
        so the same Instagram account generally gets the same fingerprint.
        """
        if self.fingerprint and not force_new:
            return self.fingerprint

        seed = self._generate_deterministic_seed() if not force_new else random.randint(0, 999999)
        rng = random.Random(seed)

        locale = rng.choice(LOCALES)
        timezone = rng.choice(TIMEZONES[locale])

        # Hardware concurrency
        concurrency_options = [4, 8, 12, 16]
        hardware_concurrency = rng.choice(concurrency_options)

        # Viewport randomization
        width = rng.randint(1200, 1400)
        height = rng.randint(700, 900)

        self.fingerprint = {
            "user_agent": rng.choice(USER_AGENTS),
            "viewport": {"width": width, "height": height},
            "locale": locale,
            "timezone_id": timezone,
            "hardware_concurrency": hardware_concurrency,
            # Fake WebGL vendor string
            "webgl_vendor": "Google Inc. (Intel)",
            "webgl_renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        }

        logger.info(
            "fingerprint_generated",
            username=self.username,
            viewport=f"{width}x{height}",
            timezone=timezone,
            hardware_concurrency=hardware_concurrency,
        )
        return self.fingerprint

    def verify_consistency(self, stored_fingerprint: dict[str, Any]) -> bool:
        """Verify a provided fingerprint matches the currently active one."""
        if not self.fingerprint:
            return False

        # Simplified consistency check, compare JSON dumps to ensure deep equality
        return json.dumps(self.fingerprint, sort_keys=True) == json.dumps(
            stored_fingerprint, sort_keys=True
        )
