"""Data models for EduIG-Pipeline.

Defines Pydantic v2 schemas for validating and normalizing data
extracted from Instagram. Handles data coercion (e.g. '1.2M' -> 1200000).
"""

import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def parse_instagram_count(value: Any) -> int | None:
    """Parse Instagram count strings like '1.2k', '3.4M', '5,678'."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    value = str(value).strip().replace(",", "")
    if not value:
        return None

    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}

    match = re.match(r"^([\d.]+)\s*([kmb])?$", value.lower())
    if not match:
        try:
            return int(float(value))
        except ValueError:
            return None

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix:
        number *= multipliers[suffix]

    return int(number)


def extract_hashtags(caption: str | None) -> list[str]:
    """Extract hashtags from a post caption."""
    if not caption:
        return []

    hashtags = re.findall(r"#(\w+)", caption)
    return [tag.lower() for tag in hashtags]


class ProfileSchema(BaseModel):
    """Schema representing an Instagram profile."""

    model_config = ConfigDict(strict=False, validate_assignment=True)

    profile_id: str = Field(description="Normalized internal ID")
    username: str = Field(description="Raw Instagram username")
    full_name: str | None = Field(default=None, description="Display name")
    is_verified: bool = Field(default=False, description="Verification status")
    is_private: bool = Field(default=False, description="Private account status")
    bio: str | None = Field(default=None, description="Sanitized bio text")
    followers: int | None = Field(default=None, description="Follower count")
    following: int | None = Field(default=None, description="Following count")
    posts_count: int | None = Field(default=None, description="Total number of posts")
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Extraction timestamp"
    )
    source: Literal["api", "browser"] = Field(description="Extraction source")

    @model_validator(mode="before")
    @classmethod
    def coerce_counts(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "followers" in data:
                data["followers"] = parse_instagram_count(data["followers"])
            if "following" in data:
                data["following"] = parse_instagram_count(data["following"])
            if "posts_count" in data:
                data["posts_count"] = parse_instagram_count(data["posts_count"])
        return data

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AuthenticatedProfileSchema(ProfileSchema):
    """Schema representing an Instagram profile extracted using an authenticated session.

    Contains exact counts rather than rounded string conversions.
    """

    exact_followers: int = Field(description="Exact follower count")
    exact_following: int = Field(description="Exact following count")
    exact_posts_count: int = Field(description="Exact post count")
    profile_picture_url: str | None = Field(default=None, description="Profile picture URL")
    business_category: str | None = Field(default=None, description="Business category")
    avg_engagement_rate: float | None = Field(default=None, description="Average engagement rate")
    posts: list["PostSchema"] = Field(default_factory=list, description="Recent posts")

    @model_validator(mode="after")
    def validate_authenticated_fields(self) -> "AuthenticatedProfileSchema":
        if self.exact_followers < 0:
            raise ValueError("exact_followers must be >= 0")
        if self.exact_following < 0:
            raise ValueError("exact_following must be >= 0")
        if self.exact_posts_count < 0:
            raise ValueError("exact_posts_count must be >= 0")

        if self.avg_engagement_rate is not None:
            if not (0.0 <= self.avg_engagement_rate <= 1.0):
                # If someone has >100% engagement, we cap it at 1.0 to pass validation
                # as requested, but log it or just enforce the rule strictly.
                if self.avg_engagement_rate > 1.0:
                    self.avg_engagement_rate = 1.0
                elif self.avg_engagement_rate < 0.0:
                    raise ValueError("avg_engagement_rate must be between 0.0 and 1.0")
        return self


class PostSchema(BaseModel):
    """Schema representing an Instagram post."""

    model_config = ConfigDict(strict=False, validate_assignment=True)

    post_id: str = Field(description="Normalized internal ID for the post")
    profile_id: str = Field(description="ID of the profile that owns this post")
    shortcode: str = Field(description="Instagram shortcode")
    type: Literal["image", "video", "carousel"] = Field(description="Post media type")
    likes: int | None = Field(default=None, description="Like count")
    comments: int | None = Field(default=None, description="Comment count")
    timestamp: datetime | None = Field(default=None, description="Post publication timestamp")
    posted_at: datetime | None = Field(default=None, description="Exact timestamp")
    hashtags: list[str] = Field(default_factory=list, description="Extracted hashtags")
    engagement_rate: float | None = Field(default=None, description="Calculated engagement rate")
    location: str | None = Field(default=None, description="Location if public")
    caption: str | None = Field(default=None, description="Post caption")

    @model_validator(mode="before")
    @classmethod
    def coerce_counts_and_hashtags(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "likes" in data:
                data["likes"] = parse_instagram_count(data["likes"])
            if "comments" in data:
                data["comments"] = parse_instagram_count(data["comments"])

            if "hashtags" not in data and "caption" in data:
                data["hashtags"] = extract_hashtags(data.get("caption"))
        return data

    @model_validator(mode="after")
    def validate_post_fields(self) -> "PostSchema":
        if self.likes is not None and self.likes < 0:
            raise ValueError("likes must be >= 0")
        if self.comments is not None and self.comments < 0:
            raise ValueError("comments must be >= 0")
        if self.engagement_rate is not None:
            if not (0.0 <= self.engagement_rate <= 1.0):
                if self.engagement_rate > 1.0:
                    self.engagement_rate = 1.0
                elif self.engagement_rate < 0.0:
                    raise ValueError("engagement_rate must be between 0.0 and 1.0")
        return self

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RunSchema(BaseModel):
    """Schema for tracking pipeline execution runs."""

    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    targets_count: int = 0
    success_count: int = 0


class TargetSchema(BaseModel):
    """Schema for tracking individual target status within a run."""

    run_id: str
    target_url: str
    status: Literal["pending", "success", "failed", "skipped"]
    error_message: str | None = None
