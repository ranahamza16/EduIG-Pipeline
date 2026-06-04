"""Authenticated worker for extracting Instagram data via injected browser session."""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from playwright.async_api import Error as PlaywrightError

from src.auth.exceptions import AuthenticationError
from src.auth.session_manager import AuthenticatedSessionManager
from src.config_loader import ConfigSchema
from src.logger import get_logger
from src.schemas import AuthenticatedProfileSchema, PostSchema


class AuthenticatedWorker:
    """Worker for extracting data using an authenticated Instagram session inside Playwright."""

    def __init__(
        self,
        session_manager: AuthenticatedSessionManager,
        config: ConfigSchema,
        logger: Any = None,
    ) -> None:
        self.session_manager = session_manager
        self.config = config
        self.logger = logger or get_logger()
        # Cache profile data to avoid navigating twice for extract_profile and extract_posts
        self._profile_cache: Dict[str, Dict[str, Any]] = {}

    async def _fetch_shared_data(self, username: str) -> dict:
        """
        Navigates to the user's profile and intercepts the internal GraphQL response 
        to get precise metrics and posts data.
        """
        if username in self._profile_cache:
            return self._profile_cache[username]

        self.logger.info("navigating_to_profile", username=username)
        page = await self.session_manager.stealth_browser.new_page()
        
        graphql_data = None
        async def handle_response(response):
            nonlocal graphql_data
            if "graphql/query" in response.url or "api/v1" in response.url:
                try:
                    data = await response.json()
                    if "data" in data and "xdt_api__v1__feed__user_timeline_graphql_connection" in data["data"]:
                        graphql_data = data
                except:
                    pass
        
        page.on("response", handle_response)
        
        try:
            url = f"https://www.instagram.com/{username}/"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)  # Allow time for GraphQL responses to parse
        except Exception as e:
            self.logger.error("profile_navigation_failed", username=username, error=str(e))
            raise ValueError(f"Failed to navigate to {url}: {e}")

        # Fetch basic profile info via web_profile_info
        api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {"x-ig-app-id": "936619743392459"}
        
        api_data = await page.evaluate(f'''async () => {{
            const res = await fetch('{api_url}', {{ headers: {json.dumps(headers)} }});
            if (!res.ok) return {{error: res.status}};
            return await res.json();
        }}''')

        user_data = api_data.get("data", {}).get("user", {})
        if not user_data:
            raise ValueError("Could not locate user data in web_profile_info response")
        
        # Inject the intercepted GraphQL timeline posts back into the user_data so the rest of the worker works
        if graphql_data and "xdt_api__v1__feed__user_timeline_graphql_connection" in graphql_data["data"]:
            timeline_conn = graphql_data["data"]["xdt_api__v1__feed__user_timeline_graphql_connection"]
            if "edge_owner_to_timeline_media" not in user_data:
                user_data["edge_owner_to_timeline_media"] = timeline_conn
            else:
                user_data["edge_owner_to_timeline_media"]["edges"] = timeline_conn.get("edges", [])
                if "count" in timeline_conn:
                    user_data["edge_owner_to_timeline_media"]["count"] = timeline_conn["count"]
        
        self._profile_cache[username] = user_data
        return user_data

    def _extract_user_from_shared_data(self, data: Any) -> Dict[str, Any] | None:
        """Helper to traverse various known structures of __sharedData."""
        if not data or not isinstance(data, dict):
            return None
            
        # Structure 1: entry_data.ProfilePage[0].graphql.user
        try:
            return data["entry_data"]["ProfilePage"][0]["graphql"]["user"]
        except (KeyError, IndexError, TypeError):
            pass
            
        # Structure 2: graphql.user
        try:
            return data["graphql"]["user"]
        except (KeyError, TypeError):
            pass

        # Structure 3: data.user (API response format)
        try:
            return data["data"]["user"]
        except (KeyError, TypeError):
            pass
            
        # If the dict itself has edge_followed_by, it might be the user object
        if "edge_followed_by" in data:
            return data

        return None

    def _parse_exact_count(self, value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        value_str = str(value).strip().replace(",", "")
        if value_str.isdigit():
            return int(value_str)
        try:
            return int(float(value_str))
        except ValueError:
            return 0

    async def extract_profile(self, username: str) -> AuthenticatedProfileSchema:
        """Extract exact real-time profile data via injected session."""
        self.logger.info("extracting_profile_authenticated", username=username)
        user_data = await self._fetch_shared_data(username)

        exact_followers = self._parse_exact_count(user_data.get("edge_followed_by", {}).get("count"))
        exact_following = self._parse_exact_count(user_data.get("edge_follow", {}).get("count"))
        exact_posts_count = self._parse_exact_count(user_data.get("edge_owner_to_timeline_media", {}).get("count"))

        profile_id = user_data.get("id", str(uuid.uuid4()))
        profile_pic = user_data.get("profile_pic_url_hd") or user_data.get("profile_pic_url", "")

        profile_dict = {
            "profile_id": profile_id,
            "username": user_data.get("username", username),
            "full_name": user_data.get("full_name"),
            "is_verified": user_data.get("is_verified", False),
            "is_private": user_data.get("is_private", False),
            "bio": user_data.get("biography", ""),
            "external_url": user_data.get("external_url"),
            "followers": exact_followers,
            "following": exact_following,
            "posts_count": exact_posts_count,
            "source": "api",
            "exact_followers": exact_followers,
            "exact_following": exact_following,
            "exact_posts_count": exact_posts_count,
            "profile_picture_url": profile_pic,
            "business_category": user_data.get("category_name") or user_data.get("business_category_name"),
        }

        return AuthenticatedProfileSchema(**profile_dict)

    async def extract_posts(self, username: str, limit: int = 12) -> List[PostSchema]:
        """Extract exactly n most recent posts with precise engagement data."""
        self.logger.info("extracting_posts_authenticated", username=username, limit=limit)
        user_data = await self._fetch_shared_data(username)

        exact_followers = self._parse_exact_count(user_data.get("edge_followed_by", {}).get("count", 1))
        if exact_followers == 0:
            exact_followers = 1  # prevent div by zero
            
        profile_id = user_data.get("id", str(uuid.uuid4()))
        is_private = user_data.get("is_private", False)

        posts: List[PostSchema] = []
        
        # If private and we don't follow, posts might be hidden
        timeline = user_data.get("edge_owner_to_timeline_media", {})
        edges = timeline.get("edges", [])

        for edge in edges:
            if len(posts) >= limit:
                break
            node = edge.get("node", {})

            likes = self._parse_exact_count(node.get("like_count", node.get("edge_media_preview_like", {}).get("count")))
            comments = self._parse_exact_count(node.get("comment_count", node.get("edge_media_to_comment", {}).get("count")))
            er = (likes + comments) / exact_followers

            caption = ""
            if isinstance(node.get("caption"), dict):
                caption = node.get("caption", {}).get("text", "")
            if not caption:
                caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                caption = caption_edges[0].get("node", {}).get("text", "") if caption_edges else ""
            
            # Extract hashtags via regex
            hashtags = re.findall(r'#\w+', caption)

            product_type = node.get("product_type", "")
            is_video = node.get("is_video", False)
            if product_type == "carousel_container" or "edge_sidecar_to_children" in node:
                post_type = "carousel"
            elif product_type == "clips" or is_video:
                post_type = "video"
            else:
                post_type = "image"

            timestamp = node.get("taken_at", node.get("taken_at_timestamp"))
            dt_timestamp = (
                datetime.fromtimestamp(timestamp, tz=timezone.utc)
                if timestamp
                else datetime.now(timezone.utc)
            )

            shortcode = node.get("code", node.get("shortcode", ""))
            
            post = PostSchema(
                post_id=node.get("id", str(uuid.uuid4())),
                profile_id=profile_id,
                shortcode=shortcode,
                type=post_type,
                likes=likes,
                comments=comments,
                timestamp=dt_timestamp,
                engagement_rate=er,
                caption=caption,
                hashtags=hashtags,
            )
            posts.append(post)

        return posts
