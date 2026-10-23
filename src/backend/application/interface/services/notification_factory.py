"""Построение текстов уведомлений.

Словарь сообщений принадлежит презентации: только она знает, как обращаться к
человеку и на каком языке. Приложение решает, когда сообщение уместно, и просит
его по имени, поэтому ни одна строка не пишется внутри use case.
"""

from __future__ import annotations

from typing import Protocol

from backend.application.interface.services.notification import Notification


class NotificationFactory(Protocol):
    """Собирает текст каждого сообщения, которое может получить человек."""

    def board_online(self) -> Notification:
        """Сообщение о том, что плата снова на связи."""

    def board_offline(self) -> Notification:
        """Сообщение о том, что плата пропала."""

    def scenario_started(self, scenario_id: str, target: str | None) -> Notification:
        """Сообщение о начале действия сценария."""

    def scenario_progress(self, scenario_id: str, temperature: float | None) -> Notification:
        """Периодическое сообщение о ходе сценария."""

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Сообщение о том, что сценарий дошёл до финальной стадии."""

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Сообщение о том, что сценарий не удалось выполнить."""
