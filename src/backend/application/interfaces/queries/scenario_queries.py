"""Читающая сторона временных сценариев."""

from __future__ import annotations

from typing import Protocol

from backend.application.dto.views.scenario_view import ScenarioView
from backend.domain.identifiers import ScenarioId, UserId


class ScenarioQueries(Protocol):
    """Чтения сценариев."""

    async def list_all(self, user_id: UserId) -> list[ScenarioView]:
        """Возвращает все сценарии аккаунта."""

    async def list_holding_priority(self, user_id: UserId) -> list[ScenarioView]:
        """Возвращает сценарии, которые пока приоритетнее автоматизации."""

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView | None:
        """Возвращает один сценарий аккаунта."""

    async def latest_holding_priority(self, user_id: UserId) -> ScenarioView | None:
        """Возвращает самый свежий сценарий, ещё держащий приоритет.

        «Тот сценарий, который я имел в виду» — заказанный последним, поэтому
        выбор опирается на сохранённые данные, а не на догадку о порядке списка.
        """
