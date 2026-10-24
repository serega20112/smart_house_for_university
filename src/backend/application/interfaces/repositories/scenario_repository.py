"""Хранилище временных сценариев одного аккаунта.

Сценарий не удаляют: он доходит до финальной стадии и остаётся в истории, поэтому
у этого репозитория нет операции удаления.
"""

from __future__ import annotations

from abc import abstractmethod

from backend.application.interfaces.repositories.base import (
    Creator,
    ListAll,
    Reader,
    Updater,
)
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.identifiers import ScenarioId, UserId


class ScenarioRepository(
    Creator[Scenario],
    Reader[Scenario, ScenarioId],
    Updater[Scenario],
    ListAll[Scenario],
):
    """Запись, чтение и изменение сценариев аккаунта."""

    @abstractmethod
    async def list_holding_priority(self, user_id: UserId) -> list[Scenario]:
        """Возвращает сценарии, которые пока приоритетнее автоматизации."""
