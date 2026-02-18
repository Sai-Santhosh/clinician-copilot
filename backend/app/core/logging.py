"""Structured JSON logging with PHI redaction."""

import logging
import re
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

settings = get_settings()

# Patterns that might indicate PHI - these get redacted
PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"\b\d{10}\b",  # Phone numbers
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",  # Dates
    r"\b(?:patient|transcript|session).*?:.*",  # Any patient/transcript data
]

# Compile patterns for efficiency
COMPILED_PHI_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in PHI_PATTERNS]


class PHIRedactingFilter(logging.Filter):
    """Filter that redacts potential PHI from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact PHI from the log record."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._redact_phi(record.msg)

        # Redact args if present
        if record.args:
            new_args: list[Any] = []
            for arg in record.args:
                if isinstance(arg, str):
                    new_args.append(self._redact_phi(arg))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)

        return True

    def _redact_phi(self, text: str) -> str:
        """Redact potential PHI from text."""
        for pattern in COMPILED_PHI_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = settings.app_name


def setup_logging() -> logging.Logger:
    """Configure structured JSON logging with PHI redaction."""
    logger = logging.getLogger("clinician_copilot")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Create JSON handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(logger)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    # Add PHI redaction filter
    handler.addFilter(PHIRedactingFilter())

    logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logging()


def get_logger() -> logging.Logger:
    """Get the application logger."""
    return logger
