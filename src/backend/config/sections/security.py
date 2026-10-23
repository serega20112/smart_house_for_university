"""Стойкость хранения паролей и допуски разбора токенов."""

from __future__ import annotations

import os


def pbkdf2_iterations() -> int:
    """Сколько итераций делает ключевая функция производная.

    Returns:
        int: Число итераций.
    """
    return int(os.getenv("SECURITY_PBKDF2_ITERATIONS", "600000"))


def password_salt_bytes() -> int:
    """Длина соли хранимого пароля.

    Returns:
        int: Байт в соли.
    """
    return int(os.getenv("SECURITY_SALT_BYTES", "16"))


def token_leeway_seconds() -> int:
    """Запас времени при проверке границ действия токена.

    Returns:
        int: Секунды допуска часов.
    """
    return int(os.getenv("SECURITY_TOKEN_LEEWAY_SEC", "0"))
