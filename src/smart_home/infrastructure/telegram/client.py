"""One bot instance, shared by polling and notifications.

Long polling and outgoing notifications used to build their own ``telegram.Bot``,
which meant two HTTP clients against the same token and no single place that knew
when the bot was up. The instance is created once here, handed to whoever needs
it, and started and stopped by the composition root through the async context
manager.

No password is ever accepted here. A chat becomes a home through a short lived
signed link token issued over HTTP by the web interface.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from telegram import Bot
from telegram.ext import Application, MessageHandler, filters

from smart_home.infrastructure.logging import get_logger

log = get_logger("telegram.client")


class TelegramUnavailableError(RuntimeError):
    """The bot is switched off or has no token.

    Args:
        message: Human readable reason.

    Returns:
        None.
    """

    def __init__(self, message: str = "the telegram bot is not configured") -> None:
        """Initialize the failure.

        Args:
            message: Human readable reason.

        Returns:
            None.
        """
        super().__init__(message)


class TelegramBotClient:
    """The single bot instance of the process, started and stopped once.

    Args:
        token: Telegram bot token, empty when the bot is switched off.

    Returns:
        None.
    """

    def __init__(self, token: str) -> None:
        """Initialize the client.

        Args:
            token: Telegram bot token, empty when the bot is switched off.

        Returns:
            None.
        """
        self._token = token
        self._bot: Bot | None = None
        self._application: Application | None = None

    @property
    def enabled(self) -> bool:
        """Return whether the bot may be started at all.

        Returns:
            bool: True when a token was configured.
        """
        return bool(self._token)

    @property
    def bot(self) -> Bot:
        """Return the shared bot instance.

        Returns:
            Bot: Shared bot instance.

        Raises:
            TelegramUnavailableError: When no token was configured.
        """
        if not self._token:
            raise TelegramUnavailableError()
        if self._bot is None:
            self._bot = Bot(token=self._token)
        return self._bot

    async def start(self, handler: object | None = None) -> None:
        """Start receiving incoming messages.

        The handler is passed in rather than bound beforehand, which keeps the
        wiring with whoever owns the wording of an answer and makes the start of
        the bot a single call.

        Args:
            handler: Coroutine taking the update and the application context, as
                the library expects it, or None to receive nothing.

        Returns:
            None.
        """
        if not self.enabled or self._application is not None:
            return
        application = Application.builder().token(self._token).bot(self.bot).build()
        await application.initialize()
        if handler is not None:
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        self._application = application
        log.info("telegram.polling_started")

    async def stop(self) -> None:
        """Stop receiving messages and release the bot.

        Returns:
            None.
        """
        application = self._application
        self._application = None
        if application is None:
            return
        if application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        log.info("telegram.polling_stopped")

    async def __aenter__(self) -> Self:
        """Start the bot.

        Returns:
            Self: Started client.
        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Stop the bot.

        Args:
            exc_type: Raised exception type or None.
            exc_val: Raised exception value or None.
            exc_tb: Raised exception traceback or None.

        Returns:
            bool: False so exceptions keep propagating.
        """
        await self.stop()
        return False
