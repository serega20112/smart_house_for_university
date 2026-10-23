"""Sending notifications into Telegram.

The chat a user is notified in is remembered rather than configured: a person who
linked their account from the messenger expects to hear about their own home
there, and the operator chat is only the fallback for somebody who never linked
one.

A delivery failure is logged and swallowed on purpose. The port says so: a
channel that is down must not break the business operation that produced the
message, but it must not disappear either.
"""

from __future__ import annotations

from backend.application.interface.services.notification import Notification
from backend.application.interface.services.user_notifier import UserNotifier
from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger
from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.telegram.client import TelegramBotClient

log = get_logger("telegram.notifier")


class TelegramNotifier(UserNotifier):
    """Delivers notifications into the chat a user linked.

    Args:
        client: The one bot instance of the process.
        sessions: Chats linked to accounts.
        operator_chat_id: Chat notified for an account that linked none.

    Returns:
        None.
    """

    def __init__(
        self,
        client: TelegramBotClient,
        sessions: RedisChatSessionStore,
        operator_chat_id: str,
    ) -> None:
        """Initialize the notifier.

        Args:
            client: The one bot instance of the process.
            sessions: Chats linked to accounts.
            operator_chat_id: Chat notified for an account that linked none.

        Returns:
            None.
        """
        self._client = client
        self._sessions = sessions
        self._operator_chat_id = operator_chat_id

    async def notify(self, user_id: UserId, notification: Notification) -> None:
        """Send a notification to the owner of a home.

        Args:
            user_id: Owner the notification is about.
            notification: Message to deliver.

        Returns:
            None.
        """
        if not self._client.enabled:
            log.info("telegram.notification_skipped", user=str(user_id), reason="bot_off")
            return
        chat_id = await self._chat_of(user_id)
        if chat_id is None:
            log.info("telegram.notification_skipped", user=str(user_id), reason="no_linked_chat")
            return
        try:
            await self._client.bot.send_message(
                chat_id=chat_id, text=notification.text, disable_notification=False
            )
        except Exception as error:
            log.error(
                "telegram.notification_failed",
                user=str(user_id),
                chat_id=chat_id,
                severity=notification.severity,
                error=str(error),
            )

    async def _chat_of(self, user_id: UserId) -> int | None:
        linked = await self._sessions.chat_of(user_id)
        if linked is not None:
            return linked
        if not self._operator_chat_id:
            return None
        try:
            return int(self._operator_chat_id)
        except ValueError:
            log.error("telegram.operator_chat_malformed", value=self._operator_chat_id)
            return None
