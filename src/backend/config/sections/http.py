"""Пул соединений исходящего HTTP-клиента."""

from __future__ import annotations

import os


def http_max_connections() -> int:
    """Сколько соединений держит пул исходящего клиента.

    Returns:
        int: Предел соединений.
    """
    return int(os.getenv("HTTP_MAX_CONNECTIONS", "20"))


def http_max_keepalive_connections() -> int:
    """Сколько соединений пул держит в готовности.

    Returns:
        int: Предел поддерживаемых соединений.
    """
    return int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "5"))
