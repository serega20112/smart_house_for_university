"""Один экземпляр бота, общий для опроса и уведомлений.

Длинный опрос и исходящие уведомления раньше строили каждый своего ``telegram.Bot``,
что значило два HTTP-клиента против одного токена и ни одного места, знающего, жив ли
бот. Экземпляр создаётся здесь один раз, отдаётся тому, кому нужен, а запускает и
останавливает его композиционный корень через асинхронный контекст-менеджер.

Пароль здесь не принимают ни какой. Чат становится домом через короткоживущий
подписанный ссылочный токен, который выдаёт по HTTP веб-интерфейс.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from types import TracebackType
from typing import Any, Self

from telegram import Bot, Update
from telegram.ext import Application, CallbackContext, MessageHandler, filters

from backend.infrastructure.logging import get_logger

log = get_logger("telegram.client")

ChatContext = CallbackContext[Any, Any, Any, Any]
MessageAnswer = Callable[[Update, ChatContext], Coroutine[Any, Any, object]]


class TelegramUnavailableError(RuntimeError):
    """Бот выключен или у него нет токена.

    Args:
        message: Причина человеческими словами.
    """

    def __init__(self, message: str = "the telegram bot is not configured") -> None:
        """Инициализирует отказ.

        Args:
            message: Причина человеческими словами.
        """
        super().__init__(message)


class TelegramBotClient:
    """Единственный экземпляр бота процесса, запущенный и остановленный один раз.

    Attributes:
        token: Токен телеграм-бота; пустой, когда бот выключен.
    """

    def __init__(self, token: str) -> None:
        """Инициализирует клиент.

        Args:
            token: Токен телеграм-бота; пустой, когда бот выключен.
        """
        self._token = token
        self._bot: Bot | None = None
        self._application: Application | None = None

    @property
    def enabled(self) -> bool:
        """Сообщает, можно ли бота вообще запускать.

        Returns:
            bool: True, когда токен настроен.
        """
        return bool(self._token)

    @property
    def bot(self) -> Bot:
        """Возвращает общий экземпляр бота.

        Returns:
            Bot: Общий экземпляр бота.

        Raises:
            TelegramUnavailableError: Когда токен не настроен.
        """
        if not self._token:
            raise TelegramUnavailableError()
        if self._bot is None:
            self._bot = Bot(token=self._token)
        return self._bot

    async def start(self, handler: MessageAnswer | None = None) -> None:
        """Начинает принимать входящие сообщения.

        Обработчик передают сюда, а не привязывают заранее: это держит связку с тем,
        кому принадлежат формулировки ответа, и делает запуск бота одним вызовом.

        Args:
            handler: Корутина, принимающая обновление и контекст приложения, как ждёт
                библиотека, или None, чтобы не принимать ничего.
        """
        if not self.enabled or self._application is not None:
            return
        application = Application.builder().token(self._token).bot(self.bot).build()
        await application.initialize()
        if handler is not None:
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
        await application.start()
        updater = application.updater
        if updater is None:
            await application.shutdown()
            raise TelegramUnavailableError("the built bot has no updater")
        await updater.start_polling(drop_pending_updates=True)
        self._application = application
        log.info("telegram.polling_started")

    async def stop(self) -> None:
        """Прекращает приём сообщений и отпускает бота."""
        application = self._application
        self._application = None
        if application is None:
            return
        updater = application.updater
        if updater is not None and updater.running:
            await updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        log.info("telegram.polling_stopped")

    async def __aenter__(self) -> Self:
        """Запускает бота.

        Returns:
            Self: Запущенный клиент.
        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Останавливает бота.

        Отказ вызывающего продолжается после того, как клиент остановлен.

        Args:
            exc_type: Тип поднятого исключения или None.
            exc_val: Само исключение или None.
            exc_tb: Его traceback или None.
        """
        await self.stop()
