"""Список сценариев аккаунта."""

from __future__ import annotations

from backend.application.interfaces.queries.scenario_queries import ScenarioQueries
from backend.domain.identifiers import UserId
from backend.domain.value_objects.scenario.scenario_view import ScenarioView


class ListScenariosUseCase:
    """Показывает сценарии аккаунта."""

    def __init__(self, queries: ScenarioQueries) -> None:
        """Собирает сценарий списка.

        Args:
            queries: Чтения сценариев.
        """
        self._queries = queries

    async def execute(self, user_id: UserId) -> list[ScenarioView]:
        """Возвращает все сценарии аккаунта.

        Args:
            user_id: Владелец сценариев.

        Returns:
            list[ScenarioView]: Сценарии аккаунта.
        """
        return await self._queries.list_all(user_id)
