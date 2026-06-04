"""Structured logging module for EduIG-Pipeline.

Configures structlog to output JSON logs for production and optionally
console-friendly logs for development. Sets up daily file rotation for
standard logs, error logs, and audit logs.
"""

import logging
import logging.handlers
import os
import sys
from typing import Any

import structlog

from src.config_loader import ConfigSchema


def mask_pii(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive PII and secrets in log events."""
    sensitive_keys = {"password", "token", "access_token", "secret", "auth_token", "session_id"}
    for key, value in event_dict.items():
        if key.lower() in sensitive_keys and isinstance(value, str):
            event_dict[key] = "***MASKED***"
    return event_dict


def configure_logging(config: ConfigSchema) -> None:
    """Configure logging behavior based on application settings.

    Args:
        config: The configuration object containing logging and path settings.
    """
    # Ensure logs directory exists
    os.makedirs(config.paths.logs, exist_ok=True)

    # Determine log level
    log_level_name = config.logging.level.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Setup standard library logging handlers
    root_logger = logging.getLogger()
    # Clear existing handlers
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    # 1. App Log: All messages (Daily rotation, configured retention)
    app_log_path = os.path.join(config.paths.logs, "app.log")
    app_handler = logging.handlers.TimedRotatingFileHandler(
        app_log_path,
        when="midnight",
        interval=config.logging.rotation_days,
        backupCount=config.logging.retention_days,
        encoding="utf-8",
    )
    app_handler.setLevel(log_level)

    # 2. Error Log: ERROR and CRITICAL only (Daily rotation, 30 days retention)
    error_log_path = os.path.join(config.paths.logs, "error.log")
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_log_path,
        when="midnight",
        interval=config.logging.rotation_days,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    # 3. Audit Log: Specialized logger for compliance (Daily rotation, manual cleanup)
    # We create a specific handler for the 'audit' logger name below
    audit_log_path = os.path.join(config.paths.logs, "audit.log")
    audit_handler = logging.handlers.TimedRotatingFileHandler(
        audit_log_path,
        when="midnight",
        interval=config.logging.rotation_days,
        backupCount=0,  # Never auto-delete
        encoding="utf-8",
    )
    # Note: We attach this handler to the specific "audit" logger, not root

    # Console Handler (if configured for dev)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Add general handlers to root logger
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

    # In some setups, we might want console logging in dev
    # For now, we always output to console in addition to files
    root_logger.addHandler(console_handler)

    # Configure the 'audit' stdlib logger
    audit_stdlib_logger = logging.getLogger("audit")
    audit_stdlib_logger.setLevel(logging.INFO)
    audit_stdlib_logger.handlers.clear()
    audit_stdlib_logger.addHandler(audit_handler)
    # Prevent audit logs from bubbling up to the root logger and appearing in app.log
    audit_stdlib_logger.propagate = False

    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        mask_pii,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Renderer selection
    renderer: Any
    if config.logging.format.lower() == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    # Configure structlog formatting standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Apply formatter to all handlers
    app_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    audit_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Configure structlog bound loggers
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "eduig") -> structlog.BoundLogger:
    """Get a bound structured logger for general application use.

    Args:
        name: Name of the logger, typically the module name.

    Returns:
        A structlog bound logger.
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def get_audit_logger() -> structlog.BoundLogger:
    """Get the specialized audit logger.

    This logger writes exclusively to the audit log file and is meant
    for compliance and tracking events.

    Returns:
        The structlog bound audit logger.
    """
    return structlog.get_logger("audit")  # type: ignore[no-any-return]
