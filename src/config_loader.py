"""Configuration loader for EduIG-Pipeline.

Provides a typed, validated configuration system using Pydantic v2.
Loads from YAML settings and allows environment variable overrides.
"""

import os
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting and circuit breaking."""

    requests_per_hour: int = Field(
        default=20, le=50, description="Max requests per hour (hard cap 50)"
    )
    base_delay: float = Field(default=5.0, description="Base delay in seconds between requests")
    max_retries: int = Field(default=3, description="Maximum number of retries on failure")
    backoff_factor: float = Field(default=2.0, description="Multiplier for exponential backoff")
    jitter_min: float = Field(default=0.5, description="Minimum jitter multiplier")
    jitter_max: float = Field(default=1.5, description="Maximum jitter multiplier")
    daily_cap: int = Field(default=50, description="Maximum requests per day")


class PathsConfig(BaseModel):
    """Configuration for file paths."""

    raw_data: str = Field(default="data/raw")
    processed: str = Field(default="data/processed")
    logs: str = Field(default="data/logs")


class ComplianceConfig(BaseModel):
    """Configuration for compliance and data retention."""

    max_profiles_per_run: int = Field(default=50)
    delete_raw_after_days: int = Field(default=7, ge=1, description="Days to keep raw data")
    require_consent: bool = Field(default=True)
    retention_enabled: bool = Field(default=True)


class BrowserConfig(BaseModel):
    """Configuration for Playwright browser extraction."""

    headless: bool = Field(default=True)
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=800)
    timeout: int = Field(default=30000, description="Browser timeout in ms")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


class APIConfig(BaseModel):
    """Configuration for Graph API interactions."""

    base_url: str = Field(default="https://graph.facebook.com/v18.0")
    timeout: float = Field(default=30.0)
    max_connections: int = Field(default=10)
    access_token: str | None = Field(default=None, description="OAuth 2.0 access token")


class LoggingConfig(BaseModel):
    """Configuration for structured logging."""

    level: str = Field(default="INFO")
    format: str = Field(default="json")
    rotation_days: int = Field(default=1)
    retention_days: int = Field(default=7)


class ConfigSchema(BaseModel):
    """Root configuration schema."""

    model_config = ConfigDict(strict=False)

    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def _apply_env_overrides(config_dict: dict[str, Any], prefix: str = "EDUIG_") -> dict[str, Any]:
    """Apply environment variable overrides to the configuration dictionary.

    Format: EDUIG_<SECTION>__<SETTING>
    Example: EDUIG_RATE_LIMIT__REQUESTS_PER_HOUR=10
    """
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue

        # Strip prefix and split by double underscore
        key_path = env_key[len(prefix) :].lower().split("__")

        if len(key_path) != 2:
            continue

        section, setting = key_path

        if section in config_dict and isinstance(config_dict[section], dict):
            # Try to coerce type based on the existing default if it exists
            if setting in config_dict[section]:
                current_val = config_dict[section][setting]
                if isinstance(current_val, bool):
                    config_dict[section][setting] = str(env_value).lower() in ("true", "1", "yes")
                elif isinstance(current_val, int):
                    try:
                        config_dict[section][setting] = int(env_value)
                    except ValueError:
                        pass
                elif isinstance(current_val, float):
                    try:
                        config_dict[section][setting] = float(env_value)
                    except ValueError:
                        pass
                else:
                    config_dict[section][setting] = env_value
            else:
                config_dict[section][setting] = env_value

    return config_dict


def load_config(yaml_path: str = "config/settings.yaml") -> ConfigSchema:
    """Load configuration from YAML and apply environment variables.

    Args:
        yaml_path: Path to the YAML configuration file.

    Returns:
        Validated ConfigSchema object.
    """
    load_dotenv()  # Load variables from .env if present

    config_dict: dict[str, Any] = {}

    # Load YAML if it exists
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            try:
                yaml_data = yaml.safe_load(f)
                if yaml_data and isinstance(yaml_data, dict):
                    config_dict = yaml_data
            except yaml.YAMLError:
                pass

    # Apply environment variable overrides
    config_dict = _apply_env_overrides(config_dict)

    # Validate and return
    return ConfigSchema(**config_dict)
