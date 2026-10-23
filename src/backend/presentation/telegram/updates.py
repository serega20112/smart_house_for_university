"""Соединение библиотеки мессенджера с разговором чата.

Библиотека зовёт один корутину-обработчик на каждое текстовое сообщение; здесь
сообщение превращается в вызов разговора, а ответ разговора — в отправку обратно
в тот же чат. Больше здесь не решается ничего: ни какая команда, ни что ответить.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackContext

from backend.infrastructure.logging import get_logger
from backend.presentation.telegram.conversation import TelegramConversation

log = get_logger("telegram.updates")


class TelegramUpdates:
    """Обработчик входящих сообщений бота.

    Args:
        conversation: Разговор, которому отдаётся сообщение чата.

    Returns:
        None.
    """

    def __init__(self, conversation: TelegramConversation) -> None:
        """Инициализирует обработчик.

        Args:
            conversation: Разговор, которому отдаётся сообщение чата.

        Returns:
            None.
        """
        self._conversation = conversation

    async def handle(self, update: Update, context: CallbackContext) -> None:
        """Отвечает на одно текстовое сообщение.

        Пустое по смыслу сообщение (стикер, файл, служебное) проходит мимо:
        отвечать на него нечем. Сбой отправки записывается в журнал и не рвёт
        цикл опроса — одно неудачное сообщение не должно выключать бота целиком.

        Args:
            update: Событие, принесённое long polling.
            context: Окружение приложения бота, дающее доступ к боту.

        Returns:
            None.
        """
        del context
        message = update.effective_message
        chat = update.effective_chat
        if message is None or chat is None or not message.text:
            return
        answer = await self._conversation.answer(chat.id, message.text)
        try:
            await message.reply_text(answer)
        except Exception as error:
            log.warning("telegram.answer_not_delivered", chat_id=chat.id, error=str(error))
