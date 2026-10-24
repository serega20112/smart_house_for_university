"""Заглушка формулировок для развёртывания без собственных сообщений."""

from __future__ import annotations

from backend.application.interfaces.services.messaging.notification import Notification
from backend.application.interfaces.services.messaging.notification_factory import (
    NotificationFactory,
)


class SilentNotification(Notification):
    """Сообщение без всякой формулировки.

    Args:
        text: Пустой текст.
    """

    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def text(self) -> str:
        """Возвращает сообщение так, как оно доходит до человека."""
        return self._text

    @property
    def severity(self) -> str:
        """Возвращает срочность сообщения."""
        return "info"


class SilentNotificationFactory(NotificationFactory):
    """Запасной вариант, когда развёртывание не приносит ни одной формулировки.

    Фразы, которые читает человек, принадлежат презентационному слою, поэтому
    контейнер не имеет права выдумывать свою: развёртывание без фабрики получает
    пустые уведомления вместо сообщений, которых никто не писал.
    """

    def board_online(self) -> Notification:
        """Возвращает сообщение о вернувшейся плате."""
        return SilentNotification("")

    def board_offline(self) -> Notification:
        """Возвращает сообщение пропавшей плате."""
        return SilentNotification("")

    def scenario_started(self, scenario_id: str, target: str | None) -> Notification:
        """Возвращает сообщение о начавшем действовать сценарии."""
        del scenario_id, target
        return SilentNotification("")

    def scenario_progress(self, scenario_id: str, temperature: float | None) -> Notification:
        """Возвращает периодическое сообщение действующего сценария."""
        del scenario_id, temperature
        return SilentNotification("")

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Возвращает сообщение о дошедшем до конца сценарии."""
        del scenario_id, reason
        return SilentNotification("")

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Возвращает сообщение о сценарии, который не удалось выполнить."""
        del scenario_id, reason
        return SilentNotification("")
