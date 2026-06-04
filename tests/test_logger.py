import json
import logging
from pathlib import Path

import pytest
import structlog

from src.config_loader import ConfigSchema, LoggingConfig, PathsConfig
from src.logger import configure_logging, get_audit_logger, get_logger


@pytest.fixture
def temp_config(tmp_path: Path) -> ConfigSchema:
    """Provide a configuration with temporary log paths."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    config = ConfigSchema()
    config.paths = PathsConfig(logs=str(logs_dir))
    config.logging = LoggingConfig(format="json", level="INFO")
    return config


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state before and after each test."""
    # Before test
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()
    logging.getLogger("audit").handlers.clear()

    yield

    # After test
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()
    logging.getLogger("audit").handlers.clear()


def test_logger_creates_directories(temp_config: ConfigSchema, tmp_path: Path):
    """Test that the logs directory is created if it doesn't exist."""
    # Point to a non-existent directory
    missing_dir = tmp_path / "missing_logs"
    temp_config.paths.logs = str(missing_dir)

    configure_logging(temp_config)

    assert missing_dir.exists()
    assert missing_dir.is_dir()


def test_app_log_receives_messages(temp_config: ConfigSchema):
    """Test that general messages go to app.log in JSON format."""
    configure_logging(temp_config)
    logger = get_logger("test_app")

    logger.info("application_started", key="value")

    app_log_file = Path(temp_config.paths.logs) / "app.log"
    assert app_log_file.exists()

    content = app_log_file.read_text()
    assert "application_started" in content
    assert "test_app" in content

    # Verify it's valid JSON
    log_data = json.loads(content.strip())
    assert log_data["event"] == "application_started"
    assert log_data["key"] == "value"
    assert log_data["logger"] == "test_app"
    assert "timestamp" in log_data


def test_error_log_filtering(temp_config: ConfigSchema):
    """Test that error.log only receives ERROR and CRITICAL messages."""
    configure_logging(temp_config)
    logger = get_logger("test_error")

    logger.info("this_is_info")
    logger.error("this_is_error", code=500)

    error_log_file = Path(temp_config.paths.logs) / "error.log"
    assert error_log_file.exists()

    content = error_log_file.read_text()
    assert "this_is_error" in content
    assert "this_is_info" not in content

    log_data = json.loads(content.strip())
    assert log_data["event"] == "this_is_error"
    assert log_data["code"] == 500


def test_audit_log_isolation(temp_config: ConfigSchema):
    """Test that audit logs go to audit.log and not app.log."""
    configure_logging(temp_config)
    app_logger = get_logger("test_app")
    audit_logger = get_audit_logger()

    app_logger.info("normal_message")
    audit_logger.info("compliance_event", user="test_user")

    app_log_file = Path(temp_config.paths.logs) / "app.log"
    audit_log_file = Path(temp_config.paths.logs) / "audit.log"

    app_content = app_log_file.read_text()
    audit_content = audit_log_file.read_text()

    # App log should have normal message, but NOT audit message (propagate=False)
    assert "normal_message" in app_content
    assert "compliance_event" not in app_content

    # Audit log should only have audit message
    assert "compliance_event" in audit_content
    assert "normal_message" not in audit_content

    log_data = json.loads(audit_content.strip())
    assert log_data["event"] == "compliance_event"
    assert log_data["user"] == "test_user"
    assert log_data["logger"] == "audit"


def test_logger_context_binding(temp_config: ConfigSchema):
    """Test that logger correctly binds context variables."""
    configure_logging(temp_config)

    # Bind context to a specific logger instance
    bound_logger = get_logger("bound_test").bind(run_id="run_123")
    bound_logger.info("task_started")

    app_log_file = Path(temp_config.paths.logs) / "app.log"
    content = app_log_file.read_text()

    log_data = json.loads(content.strip())
    assert log_data["event"] == "task_started"
    assert log_data["run_id"] == "run_123"
    assert log_data["logger"] == "bound_test"


def test_logger_pii_masking(temp_config: ConfigSchema):
    """Test that sensitive information like passwords and tokens are masked."""
    configure_logging(temp_config)
    logger = get_logger("test_pii")

    logger.info(
        "auth_attempt", username="user1", password="my_secret_password", access_token="abc123xyz"
    )

    app_log_file = Path(temp_config.paths.logs) / "app.log"
    content = app_log_file.read_text()

    log_data = json.loads(content.strip())
    assert log_data["username"] == "user1"
    assert log_data["password"] == "***MASKED***"
    assert log_data["access_token"] == "***MASKED***"
    assert "my_secret_password" not in content
    assert "abc123xyz" not in content
