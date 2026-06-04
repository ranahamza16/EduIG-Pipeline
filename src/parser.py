"""JSON Parser for EduIG-Pipeline.

Extracts fields safely from deeply nested, highly variable Instagram
JSON responses and flattens them for Pydantic validation.
"""

from typing import Any


def safe_get(data: dict[str, Any] | list[Any], *keys: str | int, default: Any = None) -> Any:
    """Safely extract nested dictionary or list values without KeyErrors or IndexErrors.

    Args:
        data: The dictionary or list to extract from.
        *keys: The sequence of keys (strings for dicts, ints for lists) to traverse.
        default: Value to return if any key is missing or invalid.

    Returns:
        The extracted value, or default.
    """
    current: Any = data
    for key in keys:
        if isinstance(current, dict) and isinstance(key, str):
            if key not in current:
                return default
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int):
            if key < 0 or key >= len(current):
                return default
            current = current[key]
        else:
            return default
    return current


def parse_profile_json(raw_data: dict[str, Any], target_id: str) -> dict[str, Any]:
    """Parse raw profile JSON into a flat schema structure.

    Args:
        raw_data: The raw dictionary extracted from the browser.
        target_id: The username of the target.

    Returns:
        A flattened dictionary mapping to ProfileSchema fields.
    """
    parsed: dict[str, Any] = {
        "profile_id": target_id,  # Will be hashed in the Normalizer
        "username": target_id,  # Store the actual username
        "full_name": None,
        "is_verified": False,
        "source": "browser",
    }

    # 1. Check for fallback DOM extraction format
    if "username" in raw_data and "followers" in raw_data and "raw_title" in raw_data:
        parsed["bio"] = raw_data.get("bio")
        meta_desc = raw_data.get("followers", "")

        if meta_desc and isinstance(meta_desc, str):
            import re

            # Extract full name handling both Python urllib and Playwright DOM variants
            if "from " in meta_desc:
                name_match = re.search(r"from (.*?)\s*\(@", meta_desc)
            else:
                name_match = re.search(r"-\s+(.*?)\s*\(@", meta_desc)

            if name_match:
                parsed["full_name"] = name_match.group(1).strip()

            followers_match = re.search(r"([\d.,]+[kmbKMB]?)\s+Followers", meta_desc, re.IGNORECASE)
            if followers_match:
                parsed["followers"] = followers_match.group(1)

            following_match = re.search(r"([\d.,]+[kmbKMB]?)\s+Following", meta_desc, re.IGNORECASE)
            if following_match:
                parsed["following"] = following_match.group(1)

            posts_match = re.search(r"([\d.,]+[kmbKMB]?)\s+Posts", meta_desc, re.IGNORECASE)
            if posts_match:
                parsed["posts_count"] = posts_match.group(1)
        else:
            parsed["followers"] = meta_desc

        return parsed

    # 2. Extract from primary GraphQL / sharedData JSON
    # Instagram JSON might nest the user under various keys depending on the endpoint
    user_node = (
        safe_get(raw_data, "graphql", "user")
        or safe_get(raw_data, "user")
        or safe_get(raw_data, "data", "user")
    )

    # 3. Graph API direct format
    if not user_node and "followers_count" in raw_data:
        user_node = raw_data

    if not user_node:
        return parsed

    # Extract ID
    parsed["profile_id"] = user_node.get("id", target_id)

    # Extract identity
    parsed["username"] = user_node.get("username", target_id)
    parsed["full_name"] = user_node.get("full_name")
    parsed["is_verified"] = user_node.get("is_verified", False)
    parsed["is_private"] = user_node.get("is_private", False)

    # Extract bio
    parsed["bio"] = user_node.get("biography")

    # Extract counts
    parsed["followers"] = safe_get(user_node, "edge_followed_by", "count") or user_node.get(
        "followers_count"
    )
    parsed["following"] = safe_get(user_node, "edge_follow", "count") or user_node.get(
        "follows_count"
    )
    parsed["posts_count"] = safe_get(
        user_node, "edge_owner_to_timeline_media", "count"
    ) or user_node.get("media_count")

    # Override source if we detect graph API fields
    if "followers_count" in raw_data:
        parsed["source"] = "api"

    return parsed


def parse_post_json(raw_data: dict[str, Any], target_id: str) -> dict[str, Any]:
    """Parse raw post JSON into a flat schema structure.

    Args:
        raw_data: The raw dictionary extracted from the browser.
        target_id: The shortcode of the post.

    Returns:
        A flattened dictionary mapping to PostSchema fields.
    """
    # Base structure
    parsed: dict[str, Any] = {
        "post_id": target_id,
        "profile_id": "unknown",  # We try to extract this if possible
        "shortcode": target_id,
        "type": "image",  # Default fallback
    }

    # Find media node
    media_node = (
        safe_get(raw_data, "graphql", "shortcode_media")
        or safe_get(raw_data, "items", 0)
        or safe_get(raw_data, "data", "shortcode_media")
    )

    # Graph API direct format
    if not media_node and ("media_type" in raw_data or "__typename" in raw_data):
        media_node = raw_data

    if not media_node:
        return parsed

    # Profile ID (owner)
    parsed["profile_id"] = safe_get(media_node, "owner", "id") or "unknown"

    # Type mapping
    typename = media_node.get("__typename", "") or media_node.get("media_type", "")
    if "Video" in typename or "VIDEO" in typename:
        parsed["type"] = "video"
    elif "Sidecar" in typename or "CAROUSEL_ALBUM" in typename:
        parsed["type"] = "carousel"
    else:
        parsed["type"] = "image"

    # Counts
    parsed["likes"] = safe_get(media_node, "edge_media_preview_like", "count") or safe_get(
        media_node, "like_count"
    )

    parsed["comments"] = (
        safe_get(media_node, "edge_media_to_parent_comment", "count")
        or safe_get(media_node, "edge_media_to_comment", "count")
        or media_node.get("comment_count")
        or media_node.get("comments_count")
    )

    # Timestamp
    parsed["timestamp"] = media_node.get("taken_at_timestamp")

    # Caption (to extract hashtags later)
    edges = safe_get(media_node, "edge_media_to_caption", "edges", default=[])
    if edges and len(edges) > 0:
        parsed["caption"] = safe_get(edges[0], "node", "text")
    elif "caption" in media_node:
        if isinstance(media_node["caption"], dict):
            parsed["caption"] = media_node["caption"].get("text")
        elif isinstance(media_node["caption"], str):
            parsed["caption"] = media_node["caption"]

    return parsed


import uuid
from datetime import datetime, timezone

from src.schemas import AuthenticatedProfileSchema, PostSchema, extract_hashtags


def parse_authenticated_profile(raw_json: dict[str, Any]) -> AuthenticatedProfileSchema:
    """Parse authenticated REST response to AuthenticatedProfileSchema."""
    user_data = safe_get(raw_json, "data", "user") or raw_json.get("user", {})
    if not user_data:
        raise ValueError("User data not found in authenticated response")

    exact_followers = int(safe_get(user_data, "edge_followed_by", "count", default=0) or 0)
    exact_following = int(safe_get(user_data, "edge_follow", "count", default=0) or 0)
    exact_posts_count = int(
        safe_get(user_data, "edge_owner_to_timeline_media", "count", default=0) or 0
    )

    username = user_data.get("username", "unknown")
    profile_id = user_data.get("id", str(uuid.uuid4()))

    posts: list[PostSchema] = []
    edges = safe_get(user_data, "edge_owner_to_timeline_media", "edges", default=[])

    total_er = 0.0
    for edge in edges:
        node = edge.get("node", {})
        post_id = node.get("id", str(uuid.uuid4()))
        likes = int(safe_get(node, "edge_media_preview_like", "count", default=0) or 0)
        comments = int(safe_get(node, "edge_media_to_comment", "count", default=0) or 0)

        er = 0.0
        if exact_followers > 0:
            er = (likes + comments) / exact_followers
        total_er += er

        caption_edges = safe_get(node, "edge_media_to_caption", "edges", default=[])
        caption = safe_get(caption_edges, 0, "node", "text", default="") if caption_edges else ""

        is_video = node.get("is_video", False)
        from typing import Literal

        post_type: Literal["image", "video", "carousel"] = "video" if is_video else "image"
        if "edge_sidecar_to_children" in node:
            post_type = "carousel"

        timestamp_val = node.get("taken_at_timestamp")
        dt_timestamp = (
            datetime.fromtimestamp(timestamp_val, tz=timezone.utc) if timestamp_val else None
        )

        post = PostSchema(
            post_id=post_id,
            profile_id=profile_id,
            shortcode=node.get("shortcode", ""),
            type=post_type,
            likes=likes,
            comments=comments,
            timestamp=dt_timestamp,
            posted_at=dt_timestamp,
            engagement_rate=er,
            caption=caption,
            hashtags=extract_hashtags(caption),
            location=safe_get(node, "location", "name"),
        )
        posts.append(post)

    avg_er = (total_er / len(posts)) if posts else 0.0

    profile_dict = {
        "profile_id": profile_id,
        "username": username,
        "full_name": user_data.get("full_name"),
        "is_verified": user_data.get("is_verified", False),
        "bio": user_data.get("biography"),
        "exact_followers": exact_followers,
        "exact_following": exact_following,
        "exact_posts_count": exact_posts_count,
        "source": "api",
        "profile_picture_url": user_data.get("profile_pic_url_hd")
        or user_data.get("profile_pic_url"),
        "business_category": user_data.get("category_name"),
        "avg_engagement_rate": avg_er,
        "posts": posts,
    }

    return AuthenticatedProfileSchema(**profile_dict)


def parse_graphql_posts(
    raw_json: dict[str, Any], profile_id: str = "unknown", exact_followers: int = 0
) -> list[PostSchema]:
    """Parse GraphQL pagination response to list of PostSchema."""
    user_node = safe_get(raw_json, "data", "user") or raw_json.get("user", {})
    edges = safe_get(user_node, "edge_owner_to_timeline_media", "edges", default=[])

    posts: list[PostSchema] = []
    for edge in edges:
        node = edge.get("node", {})
        post_id = node.get("id", str(uuid.uuid4()))
        likes = int(safe_get(node, "edge_media_preview_like", "count", default=0) or 0)
        comments = int(safe_get(node, "edge_media_to_comment", "count", default=0) or 0)

        er = 0.0
        if exact_followers > 0:
            er = (likes + comments) / exact_followers

        caption_edges = safe_get(node, "edge_media_to_caption", "edges", default=[])
        caption = safe_get(caption_edges, 0, "node", "text", default="") if caption_edges else ""

        is_video = node.get("is_video", False)
        from typing import Literal

        post_type: Literal["image", "video", "carousel"] = "video" if is_video else "image"
        if "edge_sidecar_to_children" in node:
            post_type = "carousel"

        timestamp_val = node.get("taken_at_timestamp")
        dt_timestamp = (
            datetime.fromtimestamp(timestamp_val, tz=timezone.utc) if timestamp_val else None
        )

        post = PostSchema(
            post_id=post_id,
            profile_id=profile_id,
            shortcode=node.get("shortcode", ""),
            type=post_type,
            likes=likes,
            comments=comments,
            timestamp=dt_timestamp,
            posted_at=dt_timestamp,
            engagement_rate=er,
            caption=caption,
            hashtags=extract_hashtags(caption),
            location=safe_get(node, "location", "name"),
        )
        posts.append(post)

    return posts
