"""Structured logging setup.

Log records stay machine readable and free of personal data: only device names,
channel numbers and technical identifiers are recorded.
"""

from __future__ import annotations

import json
import logging
import sys

LOGGER_ROOT = "smart_home_backend"


class JsonFormatter(logging.Formatter):
    """Formats log records as single line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as JSON.

        Args:
            record: Record to render.

        Returns:
            str: JSON line.
        """
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        context = getattr(record, "ctx", None)
        if isinstance(context, dict):
            payload.update(context)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Configure the application logger once per process.

    Args:
        level: Minimum log level.

    Returns:
        None.
    """
    root = logging.getLogger(LOGGER_ROOT)
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.setLevel(level.upper())
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger of the application namespace.

    Args:
        name: Module or component name.

    Returns:
        logging.Logger: Namespaced logger.
    """
    return logging.getLogger(f"{LOGGER_ROOT}.{name}")
