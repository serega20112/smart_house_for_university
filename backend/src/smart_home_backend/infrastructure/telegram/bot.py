"""Telegram long polling runner.

Pure transport: it accepts incoming messages and sends the reply produced by the
handler. The handler is provided by the presentation layer, so Telegram never
reaches the hardware on its own.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from smart_home_backend.infrastructure.logging_config import get_logger

log = get_logger("telegram.bot")

OnText = Callable[[int, str], Awaitable[str]]

UNKNOWN_ERROR_REPLY = "Внутренняя ошибка, попробуйте позже."


class TelegramBotRunner:
    """Runs the Telegram bot and forwards messages to a handler."""

    def __init__(self, bot_token: str, on_text: OnText, allowed_chat_id: str = "") -> None:
        """Initialize the runner.

        Args:
            bot_token: Telegram bot token.
            on_text: Coroutine turning a message into a reply.
            allowed_chat_id: Chat allowed to send commands, empty allows any.

        Returns:
            None.
        """
        self._token = bot_token
        self._on_text = on_text
        self._allowed_chat_id = str(allowed_chat_id or "")
        self._app: Any | None = None

    async def start(self) -> None:
        """Start long polling.

        Returns:
            None.
        """
        from telegram.ext import Application, MessageHandler, filters

        self._app = Application.builder().token(self._token).build()
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram bot polling started")

    async def stop(self) -> None:
        """Stop long polling.

        Returns:
            None.
        """
        if self._app is None:
            return
        try:
            if self._app.updater.running:
                await self._app.updater.stop()
            if self._app.running:
                await self._app.stop()
            await self._app.shutdown()
        finally:
            self._app = None
        log.info("Telegram bot polling stopped")

    async def _handle_message(self, update: Any, context: Any) -> None:
        message = update.effective_message
        chat = update.effective_chat
        if message is None or chat is None or not message.text:
            return
        if self._allowed_chat_id and str(chat.id) != self._allowed_chat_id:
            log.warning("Telegram message from an unauthorized chat was ignored")
            return
        try:
            reply = await self._on_text(chat.id, message.text)
        except Exception as exc:
            log.warning("Telegram handler failed", extra={"ctx": {"error": str(exc)}})
            reply = UNKNOWN_ERROR_REPLY
        await message.reply_text(reply)
