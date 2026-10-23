"""Подключение к реляционному хранилищу."""

from __future__ import annotations

import os

from backend.config.sections.parsing import as_bool


def database_url() -> str:
    """Строка подключения к реляционному хранилищу.

    Returns:
        str: Адрес базы вместе с драйвером.
    """
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://backend:backend@localhost:5432/backend",
    )


def database_echo() -> bool:
    """Логируются ли выполняемые выражения.

    Returns:
        bool: True, когда эхо включено.
    """
    return as_bool(os.getenv("DATABASE_ECHO", "0"))


def database_pool_size() -> int:
    """Сколько держится открытых соединений.

    Returns:
        int: Размер пула соединений.
    """
    return int(os.getenv("DATABASE_POOL_SIZE", "10"))


def database_pool_max_overflow() -> int:
    """Сколько соединений открывается сверх размера пула.

    Returns:
        int: Допустительный запас соединений.
    """
    return int(os.getenv("DATABASE_POOL_MAX_OVERFLOW", "10"))


def database_pool_recycle_sec() -> int:
    """Время жизни соединения в пуле.

    Returns:
        int: Секунды до пересоздания соединения.
    """
    return int(os.getenv("DATABASE_POOL_RECYCLE_SEC", "1800"))
