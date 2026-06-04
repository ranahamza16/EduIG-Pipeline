"""URL Router for EduIG-Pipeline.

Inspects incoming URLs to determine if they point to an Instagram
profile or a specific post, and extracts the target identifier.
"""

import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse


@dataclass
class TargetInfo:
    """Represents a parsed extraction target."""

    target_type: Literal["profile", "post"]
    target_id: str


def parse_url(url: str) -> TargetInfo:
    """Parse an Instagram URL to determine its type and identifier.

    Args:
        url: The raw URL to parse.

    Returns:
        TargetInfo containing the target type and identifier.

    Raises:
        ValueError: If the URL is invalid or unrecognized.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Standardize the URL format for parsing
    url = url.strip()

    # If it doesn't look like a URL (e.g. just a username), assume it's a profile
    if not url.startswith("http") and "/" not in url:
        return TargetInfo(target_type="profile", target_id=url)

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Failed to parse URL: {e}")

    # Check domain
    domain = parsed.netloc.lower()
    if domain and "instagram.com" not in domain:
        raise ValueError(f"Not an Instagram URL: {domain}")

    path = parsed.path.strip("/")

    if not path:
        raise ValueError("URL path is empty")

    path_parts = path.split("/")

    # Post patterns: /p/{shortcode}, /reel/{shortcode}, /tv/{shortcode}
    if path_parts[0] in ("p", "reel", "tv"):
        if len(path_parts) < 2 or not path_parts[1]:
            raise ValueError("Post URL missing shortcode")
        return TargetInfo(target_type="post", target_id=path_parts[1])

    # Profile pattern: /{username}
    # Usernames can contain dots, numbers, underscores
    username = path_parts[0]

    # Exclude known non-profile endpoints
    reserved_endpoints = {"explore", "developer", "about", "legal", "directory"}
    if username.lower() in reserved_endpoints:
        raise ValueError(f"Reserved endpoint cannot be used as target: {username}")

    if not re.match(r"^[a-zA-Z0-9._]+$", username):
        raise ValueError(f"Invalid characters in username: {username}")

    return TargetInfo(target_type="profile", target_id=username)


from src.config_loader import ConfigSchema


def route_authenticated(session_manager: Any, config: ConfigSchema, logger: Any = None) -> Any:
    """Route extraction to AuthenticatedWorker if authenticated, else fallback to BrowserWorker."""
    from src.logger import get_logger

    log = logger or get_logger()

    if getattr(session_manager, "is_authenticated", False):
        from src.auth.authenticated_worker import AuthenticatedWorker

        log.info(
            "routing_decision", strategy="authenticated_worker", reason="session_authenticated"
        )
        return AuthenticatedWorker(session_manager=session_manager, config=config, logger=log)

    from src.browser_worker import BrowserWorker

    log.warning(
        "routing_decision",
        strategy="browser_worker",
        reason="session_not_authenticated",
        fallback=True,
    )
    return BrowserWorker(config=config, logger_instance=log)
