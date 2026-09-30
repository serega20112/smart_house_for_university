"""HTTP server settings."""

from __future__ import annotations

import os


def app_host() -> str:
    """Return the bind host of the web server.

    Returns:
        str: Bind host.
    """
    return os.getenv("APP_HOST", "0.0.0.0")


def app_port() -> int:
    """Return the bind port of the web server.

    Returns:
        int: Bind port.
    """
    return int(os.getenv("APP_PORT", "8000"))


def log_level() -> str:
    """Return the application log level.

    Returns:
        str: Log level name.
    """
    return os.getenv("LOG_LEVEL", "INFO")


def cors_allowed_origins() -> list[str]:
    """Return the allowed CORS origins for the web interface.

    Returns:
        list[str]: Allowed origins.
    """
    return [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
