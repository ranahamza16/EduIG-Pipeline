from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas import (
    PostSchema,
    ProfileSchema,
    extract_hashtags,
    parse_instagram_count,
)


def test_parse_instagram_count():
    """Test the count parsing helper function."""
    assert parse_instagram_count(100) == 100
    assert parse_instagram_count(100.5) == 100
    assert parse_instagram_count("100") == 100
    assert parse_instagram_count("1,000") == 1000
    assert parse_instagram_count("1.2k") == 1200
    assert parse_instagram_count("3.4M") == 3400000
    assert parse_instagram_count("5b") == 5000000000
    assert parse_instagram_count("1.5 K") == 1500  # with space and uppercase
    assert parse_instagram_count(None) is None
    assert parse_instagram_count("") is None
    assert parse_instagram_count("invalid") is None


def test_extract_hashtags():
    """Test hashtag extraction helper."""
    assert extract_hashtags("No tags here") == []
    assert extract_hashtags("Hello #world") == ["world"]
    assert extract_hashtags("#multiple #Tags #HERE") == ["multiple", "tags", "here"]
    assert extract_hashtags("Attached#hashtag") == ["hashtag"]
    assert extract_hashtags(None) == []


def test_profile_schema_coercion():
    """Test that ProfileSchema correctly coerces raw data."""
    raw_data = {
        "profile_id": "test_id",
        "username": "abc",
        "followers": "1.2M",
        "following": "5,678",
        "posts_count": "10k",
        "source": "browser",
    }

    profile = ProfileSchema(**raw_data)

    assert profile.followers == 1200000
    assert profile.following == 5678
    assert profile.posts_count == 10000
    assert profile.source == "browser"


def test_profile_schema_validation_error():
    """Test that ProfileSchema enforces required fields."""
    with pytest.raises(ValidationError):
        # Missing profile_id, username_hash, and source
        ProfileSchema(followers="100")

    with pytest.raises(ValidationError):
        # Invalid source enum
        ProfileSchema(profile_id="test", username_hash="abc", source="invalid")


def test_post_schema_coercion():
    """Test that PostSchema correctly coerces raw data and extracts tags."""
    raw_data = {
        "post_id": "p123",
        "profile_id": "u456",
        "shortcode": "XYZ",
        "type": "image",
        "likes": "1.5k",
        "comments": "2,000",
        "caption": "Beautiful day! #sun #beach",
        # Notice we didn't provide 'hashtags' directly
    }

    post = PostSchema(**raw_data)

    assert post.likes == 1500
    assert post.comments == 2000
    assert post.hashtags == ["sun", "beach"]


def test_to_json_methods():
    """Test serialization methods."""
    profile = ProfileSchema(
        profile_id="id1",
        username="hash1",
        source="api",
        extracted_at=datetime(2023, 1, 1, 12, 0),
    )

    json_data = profile.to_json()
    assert isinstance(json_data, dict)
    assert json_data["profile_id"] == "id1"
    # extracted_at should be serialized to string by model_dump(mode='json')
    assert isinstance(json_data["extracted_at"], str)
