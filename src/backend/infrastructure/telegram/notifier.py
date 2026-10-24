"""Отправляет уведомления в Telegram.

Чат, в котором уведомляют человека, запоминают, а не настраивают: привязавший аккаунт из
мессенджера ждёт известий о своём доме именно там, а чат оператора — только запасной
вариант для того, кто ничего не привязал.

Отказ доставки нарочно записывают в журнал и проглатывают. Так говорит интерфейс: канал,
который лежит, не должен ломать бизнес-операцию, породившую сообщение, но и исчезать молча
он не должен.
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
    """Доставляет уведомления в чат, который привязал человек.

    Attributes:
        client: Единственный экземпляр бота процесса.
        sessions: Чаты, привязанные к аккаунтам.
        operator_chat_id: Чат, куда пишут аккаунту, ничего не привязавшему.
    """

    def __init__(
        self,
        client: TelegramBotClient,
        sessions: RedisChatSessionStore,
        operator_chat_id: str,
    ) -> None:
        """Инициализирует рассыльщик.

        Args:
            client: Единственный экземпляр бота процесса.
            sessions: Чаты, привязанные к аккаунтам.
            operator_chat_id: Чат, куда пишут аккаунту, ничего не привязавшему.
        """
        self._client = client
        self._sessions = sessions
        self._operator_chat_id = operator_chat_id

    async def notify(self, user_id: UserId, notification: Notification) -> None:
        """Отправляет уведомление владельцу дома.

        Args:
            user_id: Владелец, о котором уведомление.
            notification: Сообщение для доставки.
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
