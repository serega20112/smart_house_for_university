"""Telegram bot settings."""

from __future__ import annotations

import os


def bot_token() -> str:
    """Return the Telegram bot token.

    Returns:
        str: Bot token, empty when the bot is not configured.
    """
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def chat_id() -> str:
    """Return the chat allowed to send commands and receive notifications.

    Returns:
        str: Allowed chat id.
    """
    return os.getenv("TELEGRAM_CHAT_ID", "")


def enabled() -> bool:
    """Return whether the Telegram bot should be started.

    Returns:
        bool: True when the bot is enabled.
    """
    return os.getenv("TELEGRAM_ENABLED", "1") == "1"
