"""Читающая сторона конфигурации автоматизации."""

from __future__ import annotations

from typing import Protocol

from backend.domain.identifiers import UserId
from backend.domain.value_objects.automation.automation_view import AutomationView


class AutomationQueries(Protocol):
    """Чтения конфигурации автоматизации."""

    async def get(self, user_id: UserId) -> AutomationView:
        """Возвращает конфигурацию аккаунта.

        Аккаунт, который никогда ничего не настраивал, всё равно получает ответ:
        значения по умолчанию — часть модели чтения, а не то, что читатель должен
        придумывать сам.
        """
