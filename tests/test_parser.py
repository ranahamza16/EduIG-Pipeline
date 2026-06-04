from src.parser import parse_post_json, parse_profile_json, safe_get


def test_safe_get():
    """Test the safe dictionary extraction helper."""
    data = {"a": {"b": {"c": 42}}, "x": "not a dict"}

    assert safe_get(data, "a", "b", "c") == 42
    assert safe_get(data, "a", "missing", "c") is None
    assert safe_get(data, "missing", default="fallback") == "fallback"
    # Traversing into a non-dict should safely return default
    assert safe_get(data, "x", "y") is None


def test_parse_profile_json_graphql():
    """Test parsing standard GraphQL profile response."""
    raw = {
        "graphql": {
            "user": {
                "id": "u123",
                "biography": "Test Bio",
                "edge_followed_by": {"count": 1000},
                "edge_follow": {"count": 500},
                "edge_owner_to_timeline_media": {"count": 42},
            }
        }
    }

    parsed = parse_profile_json(raw, "testuser")

    assert parsed["profile_id"] == "u123"
    assert parsed["bio"] == "Test Bio"
    assert parsed["followers"] == 1000
    assert parsed["following"] == 500
    assert parsed["posts_count"] == 42
    assert parsed["source"] == "browser"


def test_parse_profile_json_dom_fallback():
    """Test parsing DOM fallback extraction format."""
    raw = {
        "username": "testuser",
        "raw_title": "Test User (@testuser)",
        "followers": "1.2M Followers",
        "bio": "DOM Bio",
    }

    parsed = parse_profile_json(raw, "testuser")

    assert parsed["profile_id"] == "testuser"
    assert parsed["followers"] == "1.2M"
    assert parsed["bio"] == "DOM Bio"


def test_parse_post_json_graphql():
    """Test parsing standard GraphQL post response."""
    raw = {
        "graphql": {
            "shortcode_media": {
                "owner": {"id": "u999"},
                "__typename": "GraphVideo",
                "taken_at_timestamp": 1672531200,
                "edge_media_preview_like": {"count": 5000},
                "edge_media_to_parent_comment": {"count": 120},
                "edge_media_to_caption": {
                    "edges": [{"node": {"text": "A beautiful sunset #nature"}}]
                },
            }
        }
    }

    parsed = parse_post_json(raw, "SHORTXYZ")

    assert parsed["post_id"] == "SHORTXYZ"
    assert parsed["shortcode"] == "SHORTXYZ"
    assert parsed["profile_id"] == "u999"
    assert parsed["type"] == "video"
    assert parsed["likes"] == 5000
    assert parsed["comments"] == 120
    assert parsed["timestamp"] == 1672531200
    assert parsed["caption"] == "A beautiful sunset #nature"


def test_parse_post_json_missing_data():
    """Test parsing a post with missing data gracefully."""
    raw = {}
    parsed = parse_post_json(raw, "XYZ")

    assert parsed["post_id"] == "XYZ"
    assert parsed["type"] == "image"  # Default
    assert parsed["profile_id"] == "unknown"


def test_parse_profile_json_api():
    """Test parsing Graph API profile response."""
    raw = {
        "username": "api_user",
        "biography": "API Bio",
        "followers_count": 5000,
        "follows_count": 200,
        "media_count": 100,
    }

    parsed = parse_profile_json(raw, "api_user")

    assert parsed["bio"] == "API Bio"
    assert parsed["followers"] == 5000
    assert parsed["following"] == 200
    assert parsed["posts_count"] == 100
    assert parsed["source"] == "api"


def test_parse_post_json_api():
    """Test parsing Graph API post response."""
    raw = {
        "id": "12345",
        "shortcode": "ABC",
        "media_type": "VIDEO",
        "like_count": 100,
        "comments_count": 50,
        "timestamp": "2023-10-01T12:00:00+0000",
        "caption": "API post",
    }

    parsed = parse_post_json(raw, "ABC")

    assert parsed["type"] == "video"
    assert parsed["likes"] == 100
    assert parsed["comments"] == 50
    assert parsed["caption"] == "API post"


from src.parser import parse_authenticated_profile, parse_graphql_posts
from src.schemas import AuthenticatedProfileSchema, PostSchema


def test_parse_authenticated_profile():
    """Test parsing exact counts from authenticated REST profile."""
    raw = {
        "data": {
            "user": {
                "id": "12345",
                "username": "auth_user",
                "full_name": "Auth User",
                "is_verified": True,
                "biography": "Hello #world",
                "edge_followed_by": {"count": 1247},
                "edge_follow": {"count": 500},
                "edge_owner_to_timeline_media": {
                    "count": 2,
                    "edges": [
                        {
                            "node": {
                                "id": "p1",
                                "shortcode": "SHORT1",
                                "edge_media_preview_like": {"count": 100},
                                "edge_media_to_comment": {"count": 24},
                                "taken_at_timestamp": 1672531200,
                                "edge_media_to_caption": {
                                    "edges": [{"node": {"text": "My post #fun"}}]
                                },
                            }
                        },
                        {
                            "node": {
                                "id": "p2",
                                "shortcode": "SHORT2",
                                "edge_media_preview_like": {"count": 200},
                                "edge_media_to_comment": {"count": 50},
                                "taken_at_timestamp": 1672531200,
                                "edge_sidecar_to_children": {"edges": []},
                            }
                        },
                    ],
                },
            }
        }
    }

    schema = parse_authenticated_profile(raw)

    assert isinstance(schema, AuthenticatedProfileSchema)
    assert schema.exact_followers == 1247
    assert schema.exact_following == 500
    assert schema.exact_posts_count == 2
    assert schema.username == "auth_user"
    assert schema.is_verified is True

    assert schema.avg_engagement_rate is not None
    assert 0.14 < schema.avg_engagement_rate < 0.16

    assert len(schema.posts) == 2
    assert schema.posts[0].likes == 100
    assert schema.posts[0].comments == 24
    assert schema.posts[0].engagement_rate == 124 / 1247
    assert schema.posts[0].type == "image"
    assert "fun" in schema.posts[0].hashtags
    assert schema.posts[1].type == "carousel"


def test_parse_graphql_posts():
    """Test parsing exact posts from authenticated GraphQL pagination."""
    raw = {
        "data": {
            "user": {
                "edge_owner_to_timeline_media": {
                    "edges": [
                        {
                            "node": {
                                "id": "p3",
                                "shortcode": "SHORT3",
                                "is_video": True,
                                "edge_media_preview_like": {"count": 50},
                                "edge_media_to_comment": {"count": 5},
                                "taken_at_timestamp": 1672531200,
                            }
                        }
                    ]
                }
            }
        }
    }

    posts = parse_graphql_posts(raw, profile_id="12345", exact_followers=1000)

    assert len(posts) == 1
    post = posts[0]
    assert post.likes == 50
    assert post.comments == 5
    assert post.type == "video"
    assert post.engagement_rate == 55 / 1000
    assert post.profile_id == "12345"
