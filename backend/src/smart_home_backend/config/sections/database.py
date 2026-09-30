"""Database settings."""

from __future__ import annotations

import os


def database_url() -> str:
    """Return the async SQLAlchemy connection URL.

    Returns:
        str: Connection URL for SQLite or PostgreSQL.
    """
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./smart_home.db")


def database_echo() -> bool:
    """Return whether SQL statements should be logged.

    Returns:
        bool: True when SQL echo is enabled.
    """
    return os.getenv("DATABASE_ECHO", "0") == "1"
