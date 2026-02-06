"""Structured logging configuration.

JSON logs with automatic context binding. Uses structlog with stdlib integration.
Request-scoped context (like request_id) is automatically included in all logs
via structlog.contextvars.
"""

import logging
import logging.config
import sys
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from structlog.stdlib import BoundLogger


def _add_timestamp(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add ISO 8601 UTC timestamp with timezone offset."""
    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


class LoggingSettings(BaseSettings):
    """Logging settings from environment variables."""

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


def configure_logging(settings: LoggingSettings) -> None:
    """Configure structlog with JSON output to stdout.

    Call once at application startup. After this, all loggers created via
    get_logger() will output JSON with automatic context binding.
    """
    # Processors run on every log event
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,  # Auto-include bound context
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _add_timestamp,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                    "foreign_pre_chain": processors,
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": sys.stdout,
                },
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": settings.log_level,
                    "propagate": True,
                },
            },
        }
    )


# Configure once at module import
_settings = LoggingSettings()
configure_logging(_settings)


def get_logger(name: str) -> BoundLogger:
    """Get a structured logger.

    Args:
        name: Logger name, typically __name__

    Returns:
        Logger that outputs JSON with automatic context binding.

    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=123)
        # Output: {"event": "user_login", "user_id": 123, "level": "info", ...}
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]
