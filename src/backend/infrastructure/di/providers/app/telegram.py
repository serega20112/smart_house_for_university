"""Telegram: единственный бот, токены привязки и доставка сообщений."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interfaces.services.messaging.user_notifier import UserNotifier
from backend.application.interfaces.services.security.session_token_issuer import SessionTokenIssuer
from backend.config.settings import Settings
from backend.infrastructure.brokers.chat_sessions import RedisChatSessionStore
from backend.infrastructure.security.link_tokens import TelegramLinkTokenIssuer
from backend.infrastructure.telegram.client import TelegramBotClient
from backend.infrastructure.telegram.notifier import TelegramNotifier

APP = Scope.APP


class TelegramProvider(Provider):
    """Один экземпляр бота и то, для чего его используют."""

    @provide(scope=APP)
    def bot(self, settings: Settings) -> TelegramBotClient:
        """Собирает единственный экземпляр бота процесса."""
        return TelegramBotClient(settings.telegram_bot_token)

    @provide(scope=APP)
    def link_tokens(
        self, tokens: SessionTokenIssuer, settings: Settings
    ) -> TelegramLinkTokenIssuer:
        """Собирает источник одноразовых токенов привязки."""
        return TelegramLinkTokenIssuer(
            tokens,
            lifetime_minutes=settings.telegram_link_lifetime_min,
        )

    @provide(scope=APP)
    def notifier(
        self,
        bot: TelegramBotClient,
        sessions: RedisChatSessionStore,
        settings: Settings,
    ) -> UserNotifier:
        """Собирает канал, которым сообщение доходит до человека."""
        return TelegramNotifier(
            client=bot,
            sessions=sessions,
            operator_chat_id=settings.telegram_notify_chat_id,
        )
