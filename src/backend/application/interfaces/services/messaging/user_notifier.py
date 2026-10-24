"""Доставка уведомления владельцу дома."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.application.interfaces.services.messaging.notification import Notification
from backend.domain.identifiers import UserId


class UserNotifier(ABC):
    """Относит уведомление человеку, чей дом оно касается."""

    @abstractmethod
    async def notify(self, user_id: UserId, notification: Notification) -> None:
        """Доставляет уведомление.

        Упавший канал не должен ломать бизнес-операцию, которая это уведомление
        породила, поэтому реализации только сообщают о неудаче и идут дальше.
        """
