"""Транспорт бота и доставка сообщений в мессенджер.

``client``
    единственный экземпляр ``telegram.Bot``, разделяемый опросом и уведомлениями.
``linking``
    короткие подписанные токены, привязывающие чат к аккаунту.
``notifier``
    доставка уведомлений в чат, который человек привязал.

Разговором — «кому принадлежит чат и что ответить» — заведует презентационный
слой: там знают язык человека. Через этот пакет не проходит ни одного пароля.
"""

from backend.infrastructure.security.link_tokens import TelegramLinkTokenIssuer
from backend.infrastructure.telegram.client import (
    TelegramBotClient,
    TelegramUnavailableError,
)
from backend.infrastructure.telegram.notifier import TelegramNotifier

__all__ = [
    "TelegramBotClient",
    "TelegramLinkTokenIssuer",
    "TelegramNotifier",
    "TelegramUnavailableError",
]
