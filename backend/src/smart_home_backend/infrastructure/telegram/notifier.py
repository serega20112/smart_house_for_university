"""Telegram notification adapter."""

from __future__ import annotations

from typing import Any

from smart_home_backend.application.interface.services import Notifier
from smart_home_backend.infrastructure.logging_config import get_logger

log = get_logger("telegram.notifier")


class TelegramNotifier(Notifier):
    """Sends notifications into the configured chat."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """Initialize the notifier.

        Args:
            bot_token: Telegram bot token.
            chat_id: Chat receiving the notifications.

        Returns:
            None.
        """
        self._token = bot_token
        self._chat_id = chat_id
        self._bot: Any | None = None

    async def notify(self, text: str) -> None:
        """Send a notification, ignoring delivery failures.

        A failing notification must never break a business operation, so every
        error is logged and swallowed.

        Args:
            text: Notification text.

        Returns:
            None.
        """
        if not self._token or not self._chat_id:
            log.debug("Telegram notification skipped, bot is not configured")
            return
        try:
            await self._bot_instance().send_message(chat_id=self._chat_id, text=text)
        except Exception as exc:
            log.warning("Telegram notification failed", extra={"ctx": {"error": str(exc)}})

    def _bot_instance(self) -> Any:
        if self._bot is None:
            from telegram import Bot

            self._bot = Bot(token=self._token)
        return self._bot
