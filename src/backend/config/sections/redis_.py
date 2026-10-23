"""Хранилище изменчивого и разделяемого состояния."""

from __future__ import annotations

import os


def redis_url() -> str:
    """Строка подключения к хранилищу.

    Returns:
        str: Адрес Redis.
    """
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def redis_password() -> str | None:
    """Пароль хранилища, когда его спрашивают.

    Returns:
        str | None: Пароль или None, если он не задан.
    """
    return os.getenv("REDIS_PASSWORD") or None


def redis_key_prefix() -> str:
    """Префикс каждого ключа этого развёртывания.

    Returns:
        str: Префикс ключей.
    """
    return os.getenv("REDIS_KEY_PREFIX", "smart-home")
