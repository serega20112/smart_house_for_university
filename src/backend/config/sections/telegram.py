"""Бот Telegram, который разносит уведомления и принимает команды."""

from __future__ import annotations

import os

from backend.config.sections.parsing import as_bool


def telegram_enabled() -> bool:
    """Запускается ли бот вообще.

    Returns:
        bool: True, когда бот включён.
    """
    return as_bool(os.getenv("TELEGRAM_ENABLED", "0"))


def telegram_bot_token() -> str:
    """Токен, которым бот обращается к Telegram.

    Returns:
        str: Токен или пустая строка, если он не задан.
    """
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def telegram_notify_chat_id() -> str:
    """Чат, в который доставляются уведомления оператора.

    Returns:
        str: Идентификатор чата.
    """
    return os.getenv("TELEGRAM_NOTIFY_CHAT_ID", "")


def telegram_link_lifetime_min() -> int:
    """Сколько живёт ссылка привязки аккаунта к чату.

    Returns:
        int: Минуты действия ссылки.
    """
    return int(os.getenv("TELEGRAM_LINK_LIFETIME_MIN", "10"))
