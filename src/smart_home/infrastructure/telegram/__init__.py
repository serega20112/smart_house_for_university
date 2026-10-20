"""Telegram bot of the smart home smart_home.

``client``
    the one ``telegram.Bot`` instance, shared by polling and notifications.
``router``
    transport of a conversation: which account a chat belongs to and what a link
    token does.
``linking``
    the short lived signed tokens that link a chat to an account.
``notifier``
    delivery of notifications into the chat a user linked.

No password ever travels through this package.
"""

from smart_home.infrastructure.telegram.client import (
    TelegramBotClient,
    TelegramUnavailableError,
)
from smart_home.infrastructure.telegram.linking import TelegramLinkTokenIssuer
from smart_home.infrastructure.telegram.notifier import TelegramNotifier
from smart_home.infrastructure.telegram.router import TelegramMessageRouter, TelegramRouting

__all__ = [
    "TelegramBotClient",
    "TelegramLinkTokenIssuer",
    "TelegramMessageRouter",
    "TelegramNotifier",
    "TelegramRouting",
    "TelegramUnavailableError",
]
