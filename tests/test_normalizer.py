from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.normalizer import (
    hash_identifier,
    mask_identifier,
    normalize_post,
    normalize_profile,
)
from src.schemas import PostSchema, ProfileSchema


def test_hash_identifier():
    """Test SHA-256 hashing."""
    h1 = hash_identifier("test_user")
    h2 = hash_identifier("test_user")

    assert h1 == h2
    assert len(h1) == 64
    assert hash_identifier("") == ""


def test_mask_identifier():
    """Test identifier masking for logs."""
    assert mask_identifier("rana_hamza16") == "r***16"
    assert mask_identifier("abc") == "a***c"
    assert mask_identifier("a") == "***"
    assert mask_identifier("") == ""


def test_parse_human_number():
    """Test human-readable number parsing."""
    from src.normalizer import parse_human_number

    assert parse_human_number(123) == 123
    assert parse_human_number("1,234") == 1234
    assert parse_human_number("1.5M") == 1500000
    assert parse_human_number("10K") == 10000
    assert parse_human_number("1.2b") == 1200000000
    assert parse_human_number("invalid") is None
    assert parse_human_number(None) is None


def test_normalize_profile_success():
    """Test full profile normalization flow."""
    raw = {"graphql": {"user": {"id": "internal_id_123", "edge_followed_by": {"count": "1.2M"}}}}

    profile = normalize_profile(raw, "target_user")

    assert isinstance(profile, ProfileSchema)
    assert profile.followers == 1200000  # Pydantic coercion worked
    assert profile.username == "target_user"
    assert profile.profile_id == "internal_id_123"  # Kept internal ID


def test_normalize_profile_missing_id():
    """Test profile normalization when internal ID is missing."""
    raw = {"followers": "1.2M", "username": "test", "raw_title": "test"}  # Fallback format

    profile = normalize_profile(raw, "target_user")

    # profile_id should fallback to the username hash
    assert profile.profile_id == hash_identifier("target_user")
    assert profile.username == "target_user"


def test_normalize_post_success():
    """Test full post normalization flow."""
    raw = {
        "graphql": {
            "shortcode_media": {
                "__typename": "GraphImage",
                "edge_media_preview_like": {"count": "10,500"},
            }
        }
    }

    post = normalize_post(raw, "XYZ")

    assert isinstance(post, PostSchema)
    assert post.likes == 10500  # Pydantic coercion worked
    assert post.post_id == hash_identifier("XYZ")  # Shortcode was hashed
    assert post.shortcode == "XYZ"


@patch("src.normalizer.parse_profile_json")
def test_normalize_validation_error(mock_parse):
    """Test validation failure bubbles up."""
    # Force parser to return a dictionary that fails Pydantic validation
    mock_parse.return_value = {
        "profile_id": "test",
        "username": "hash",
        "source": "invalid_enum_value",  # This will fail Literal["api", "browser"]
    }

    with pytest.raises(ValidationError):
        normalize_profile({}, "test")


def test_normalize_post_unknown_profile():
    """Test post normalization when profile is unknown."""
    raw = {}
    post = normalize_post(raw, "XYZ")
    assert post.profile_id == hash_identifier("unknown")


def test_normalize_post_engagement_rate():
    """Test calculation of engagement metrics."""
    raw = {
        "graphql": {
            "shortcode_media": {
                "__typename": "GraphImage",
                "edge_media_preview_like": {"count": 1000},
                "edge_media_to_comment": {"count": 100},
            }
        }
    }

    # Engagement rate = (1000 + 100) / 10000 = 0.11
    post = normalize_post(raw, "XYZ", profile_followers=10000)

    assert post.likes == 1000
    assert post.comments == 100
    assert post.engagement_rate == 0.11

    # Missing followers should yield None
    post_no_followers = normalize_post(raw, "XYZ")
    assert post_no_followers.engagement_rate is None


from datetime import datetime, timedelta, timezone

from src.normalizer import normalize_authenticated_data
from src.schemas import AuthenticatedProfileSchema


def test_normalize_authenticated_data_success():
    """Test authenticated normalization with PII stripping and ER calculation."""
    profile = AuthenticatedProfileSchema(
        profile_id="auth_id",
        username="raw_username",
        full_name="Raw Name",
        is_verified=True,
        bio="Hello! email me at test@example.com or call +1234567890. Link: https://example.com",
        followers=1000,
        following=100,
        posts_count=2,
        extracted_at=datetime.now(timezone.utc),
        source="api",
        exact_followers=1000,
        exact_following=100,
        exact_posts_count=2,
    )
    posts = [
        PostSchema(
            post_id="p1",
            profile_id="auth_id",
            shortcode="s1",
            type="image",
            likes=100,
            comments=0,
            engagement_rate=0.1,
        ),
        PostSchema(
            post_id="p2",
            profile_id="auth_id",
            shortcode="s2",
            type="image",
            likes=200,
            comments=0,
            engagement_rate=0.2,
        ),
    ]

    with patch("src.normalizer.get_profile_extracted_at", return_value=None):
        norm_profile, norm_posts = normalize_authenticated_data(profile, posts)

    assert norm_profile is not None
    # Username should be hashed
    assert norm_profile.username == hash_identifier("raw_username")
    # Bio should be scrubbed
    assert "[EMAIL_REMOVED]" in norm_profile.bio
    assert "[PHONE_REMOVED]" in norm_profile.bio
    assert "[LINK_REMOVED]" in norm_profile.bio
    # ER calculated
    assert norm_profile.avg_engagement_rate == pytest.approx(0.15)
    # Posts IDs hashed
    assert norm_posts[0].post_id == hash_identifier("p1")
    assert norm_posts[1].post_id == hash_identifier("p2")


def test_normalize_authenticated_data_deduplication():
    """Test deduplication skip when existing profile is newer."""
    profile = AuthenticatedProfileSchema(
        profile_id="auth_id",
        username="raw_username",
        extracted_at=datetime.now(timezone.utc) - timedelta(days=1),
        source="api",
        exact_followers=1000,
        exact_following=100,
        exact_posts_count=2,
    )

    newer_time = datetime.now(timezone.utc)

    with patch("src.normalizer.get_profile_extracted_at", return_value=newer_time):
        norm_profile, norm_posts = normalize_authenticated_data(profile, [])

    assert norm_profile is None
    assert norm_posts == []
