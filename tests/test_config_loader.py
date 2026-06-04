import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config_loader import ConfigSchema, _apply_env_overrides, load_config


def test_default_config_loads_without_yaml():
    """Test that configuration loads with defaults if YAML is missing."""
    config = load_config("nonexistent_path.yaml")

    # Assert defaults from Pydantic schema
    assert config.rate_limit.requests_per_hour == 20
    assert config.rate_limit.max_retries == 3
    assert config.paths.raw_data == "data/raw"
    assert config.compliance.delete_raw_after_days == 7
    assert config.browser.headless is True


def test_apply_env_overrides():
    """Test that environment variables correctly override config values."""
    base_dict = {
        "rate_limit": {"requests_per_hour": 20, "base_delay": 5.0},
        "compliance": {"require_consent": True},
        "browser": {"user_agent": "default"},
    }

    with patch.dict(
        os.environ,
        {
            "EDUIG_RATE_LIMIT__REQUESTS_PER_HOUR": "15",
            "EDUIG_RATE_LIMIT__BASE_DELAY": "2.5",
            "EDUIG_COMPLIANCE__REQUIRE_CONSENT": "false",
            "EDUIG_BROWSER__USER_AGENT": "custom_agent",
            "IGNORE_ME": "value",
        },
        clear=True,
    ):

        result = _apply_env_overrides(base_dict)

        assert result["rate_limit"]["requests_per_hour"] == 15
        assert result["rate_limit"]["base_delay"] == 2.5
        assert result["compliance"]["require_consent"] is False
        assert result["browser"]["user_agent"] == "custom_agent"


def test_apply_env_overrides_type_coercion():
    base_dict = {
        "rate_limit": {"max_retries": 3, "jitter_min": 0.5},
        "compliance": {"require_consent": True},
        "browser": {"headless": False},
    }
    with patch.dict(
        os.environ,
        {
            "EDUIG_RATE_LIMIT__MAX_RETRIES": "invalid",
            "EDUIG_RATE_LIMIT__JITTER_MIN": "invalid",
            "EDUIG_COMPLIANCE__REQUIRE_CONSENT": "1",
            "EDUIG_BROWSER__HEADLESS": "true",
            "EDUIG_UNKNOWN__SETTING": "val",
        },
        clear=True,
    ):
        result = _apply_env_overrides(base_dict)
        # Should retain old value because 'invalid' fails coercion
        assert result["rate_limit"]["max_retries"] == 3
        assert result["rate_limit"]["jitter_min"] == 0.5
        assert result["compliance"]["require_consent"] is True
        assert result["browser"]["headless"] is True


def test_validation_errors():
    """Test that schema validation enforces limits."""
    # Test requests_per_hour > 50
    with pytest.raises(ValidationError) as exc_info:
        ConfigSchema(rate_limit={"requests_per_hour": 100})
    assert "requests_per_hour" in str(exc_info.value)

    # Test delete_raw_after_days < 1
    with pytest.raises(ValidationError) as exc_info:
        ConfigSchema(compliance={"delete_raw_after_days": 0})
    assert "delete_raw_after_days" in str(exc_info.value)


def test_load_config_with_real_yaml():
    """Test loading the actual settings.yaml file."""
    # Assumes run from project root where config/settings.yaml exists
    yaml_path = "config/settings.yaml"
    if not os.path.exists(yaml_path):
        pytest.skip("settings.yaml not found, skipping integration test")

    config = load_config(yaml_path)
    assert isinstance(config, ConfigSchema)
    # The default in settings.yaml for requests_per_hour is 20
    assert config.rate_limit.requests_per_hour == 20


def test_load_config_yaml_error(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("invalid: yaml: :")
    config = load_config(str(bad_yaml))
    assert config.rate_limit.requests_per_hour == 20
