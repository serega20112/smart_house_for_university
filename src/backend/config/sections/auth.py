"""Подпись сессий и время её жизни."""

from __future__ import annotations

import os

MIN_SECRET_LENGTH = 32


def auth_token_secret() -> str:
    """Секрет, которым подписываются токены сессий.

    Returns:
        str: Секрет из окружения.

    Raises:
        RuntimeError: Когда секрет не задан или короче минимальной длины.
    """
    value = os.getenv("AUTH_TOKEN_SECRET", "")
    if len(value) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"AUTH_TOKEN_SECRET must be set and at least {MIN_SECRET_LENGTH} characters long"
        )
    return value


def auth_session_lifetime_minutes() -> int:
    """Сколько живёт выданная сессия.

    Returns:
        int: Минуты жизни сессии.
    """
    return int(os.getenv("AUTH_SESSION_LIFETIME_MINUTES", "720"))
