import pytest

from src.router import parse_url


def test_parse_url_profile():
    """Test parsing profile URLs."""
    # Standard formats
    assert parse_url("https://www.instagram.com/rana_hamza16/").target_type == "profile"
    assert parse_url("https://www.instagram.com/rana_hamza16/").target_id == "rana_hamza16"

    assert parse_url("https://instagram.com/some.user_name").target_type == "profile"
    assert parse_url("https://instagram.com/some.user_name").target_id == "some.user_name"

    # Raw username
    assert parse_url("just_a_username").target_type == "profile"
    assert parse_url("just_a_username").target_id == "just_a_username"

    # With query params
    assert parse_url("https://instagram.com/test_user?igshid=123").target_id == "test_user"


def test_parse_url_post():
    """Test parsing post URLs."""
    # Standard posts
    assert parse_url("https://www.instagram.com/p/C123abc/").target_type == "post"
    assert parse_url("https://www.instagram.com/p/C123abc/").target_id == "C123abc"

    # Reels
    assert parse_url("https://instagram.com/reel/XYZ987/").target_type == "post"
    assert parse_url("https://instagram.com/reel/XYZ987/").target_id == "XYZ987"

    # IGTV
    assert parse_url("https://instagram.com/tv/DEF456").target_type == "post"
    assert parse_url("https://instagram.com/tv/DEF456").target_id == "DEF456"

    # With query params
    assert (
        parse_url("https://instagram.com/p/C123abc?utm_source=ig_web_copy_link").target_id
        == "C123abc"
    )


def test_parse_url_invalid():
    """Test parsing invalid URLs raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_url("")

    with pytest.raises(ValueError, match="Not an Instagram URL"):
        parse_url("https://twitter.com/username")

    with pytest.raises(ValueError, match="URL path is empty"):
        parse_url("https://instagram.com/")

    with pytest.raises(ValueError, match="Reserved endpoint"):
        parse_url("https://instagram.com/explore")

    with pytest.raises(ValueError, match="Invalid characters"):
        parse_url("https://instagram.com/user!name")

    with pytest.raises(ValueError, match="Post URL missing shortcode"):
        parse_url("https://instagram.com/p/")
