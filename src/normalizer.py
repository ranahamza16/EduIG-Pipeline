"""Data Normalizer for EduIG-Pipeline.

Orchestrates the data pipeline by passing raw data to the parser,
applying PII hashing rules, and validating against Pydantic schemas.
"""

import hashlib
from typing import Any

from src.compliance import scrub_bio
from src.logger import get_logger
from src.parser import parse_post_json, parse_profile_json
from src.schemas import AuthenticatedProfileSchema, PostSchema, ProfileSchema
from src.storage import get_profile_extracted_at


def hash_identifier(identifier: str) -> str:
    """Generate a secure SHA-256 hash for PII stripping.

    Args:
        identifier: The raw string to hash (e.g. username).

    Returns:
        A hex string of the SHA-256 hash.
    """
    if not identifier:
        return ""
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()


def parse_human_number(val: Any) -> int | None:
    """Convert human-readable numbers like '1.5m' or '10k' to integers.

    Args:
        val: The value to parse (int, float, or str).

    Returns:
        The integer representation, or None if invalid.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)

    s = str(val).lower().replace(",", "").strip()
    if not s:
        return None

    multiplier = 1
    if s.endswith("k"):
        multiplier = 1000
        s = s[:-1]
    elif s.endswith("m"):
        multiplier = 1000000
        s = s[:-1]
    elif s.endswith("b"):
        multiplier = 1000000000
        s = s[:-1]

    try:
        return int(float(s) * multiplier)
    except ValueError:
        return None


def mask_identifier(identifier: str) -> str:
    """Mask an identifier for safe logging (e.g. rana_hamza16 -> r***16).

    Args:
        identifier: The raw string to mask.

    Returns:
        The masked string.
    """
    if not identifier:
        return ""

    length = len(identifier)
    if length <= 2:
        return "***"

    # Keep first and last 2 characters visible if long enough
    if length > 5:
        return f"{identifier[0]}***{identifier[-2:]}"

    # Short names
    return f"{identifier[0]}***{identifier[-1]}"


def normalize_profile(raw_data: dict[str, Any], target_id: str) -> ProfileSchema:
    """Normalize and validate raw profile JSON.

    Args:
        raw_data: The messy JSON from the browser extraction.
        target_id: The requested target username.

    Returns:
        A validated ProfileSchema with PII hashed.

    Raises:
        pydantic.ValidationError: If the schema constraints fail.
    """
    # 1. Flatten the messy JSON
    flat_data = parse_profile_json(raw_data, target_id)

    # 2. Assign unique ID (hash of target)
    username_hash = hash_identifier(target_id)

    # If the parser couldn't find an internal ID, use the hash as the profile_id
    if flat_data.get("profile_id") == target_id:
        flat_data["profile_id"] = username_hash

    # Parse numeric fields
    for field in ["followers", "following", "posts_count"]:
        if field in flat_data:
            flat_data[field] = parse_human_number(flat_data[field])

    # 3. Apply bio scrubbing for PII
    if "bio" in flat_data and flat_data["bio"]:
        flat_data["bio"] = scrub_bio(flat_data["bio"])

    # 4. Validate and coerce types via Pydantic
    return ProfileSchema(**flat_data)


def normalize_post(
    raw_data: dict[str, Any], target_id: str, profile_followers: int | None = None
) -> PostSchema:
    """Normalize and validate raw post JSON.

    Args:
        raw_data: The messy JSON from the browser extraction.
        target_id: The requested target shortcode.
        profile_followers: Optional follower count of the profile for engagement metrics.

    Returns:
        A validated PostSchema.

    Raises:
        pydantic.ValidationError: If the schema constraints fail.
    """
    # 1. Flatten the messy JSON
    flat_data = parse_post_json(raw_data, target_id)

    # 2. Hash IDs for consistency/safety
    flat_data["post_id"] = hash_identifier(target_id)

    # If profile_id is unknown, ensure it is set cleanly
    if flat_data.get("profile_id") == "unknown":
        flat_data["profile_id"] = hash_identifier("unknown")

    # Parse numeric fields
    for field in ["likes", "comments"]:
        if field in flat_data:
            flat_data[field] = parse_human_number(flat_data[field])

    # 3. Validate and coerce types via Pydantic
    post = PostSchema(**flat_data)

    # 4. Calculate Engagement Rate if followers are known
    if profile_followers and profile_followers > 0:
        likes = post.likes or 0
        comments = post.comments or 0
        post.engagement_rate = round((likes + comments) / profile_followers, 4)

    return post


def normalize_authenticated_data(
    profile: AuthenticatedProfileSchema, posts: list[PostSchema]
) -> tuple[AuthenticatedProfileSchema | None, list[PostSchema]]:
    """Normalize authenticated profile and posts with PII stripping and deduplication."""
    logger = get_logger()

    # 1. Deduplication check
    existing_extracted_at = get_profile_extracted_at(profile.profile_id)
    if existing_extracted_at and profile.extracted_at < existing_extracted_at:
        logger.info("deduplication_skip", profile_id=profile.profile_id, reason="existing_is_newer")
        return None, []

    # 2. PII Stripping (same as unauthenticated rules)
    profile.bio = scrub_bio(profile.bio)

    # 3. Calculate avg_engagement_rate for the profile
    if posts:
        valid_rates = [p.engagement_rate for p in posts if p.engagement_rate is not None]
        if valid_rates:
            profile.avg_engagement_rate = sum(valid_rates) / len(valid_rates)
            if profile.avg_engagement_rate > 1.0:
                profile.avg_engagement_rate = 1.0
            elif profile.avg_engagement_rate < 0.0:
                profile.avg_engagement_rate = 0.0

    # 4. Normalize posts
    for post in posts:
        post.post_id = hash_identifier(post.post_id)
        post.profile_id = profile.profile_id

        if post.engagement_rate is not None:
            if post.engagement_rate > 1.0:
                post.engagement_rate = 1.0
            elif post.engagement_rate < 0.0:
                post.engagement_rate = 0.0

    return profile, posts
