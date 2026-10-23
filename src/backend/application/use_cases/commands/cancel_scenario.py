"""Отменить сценарий, который человек имел в виду."""

from __future__ import annotations

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import ScenarioNotFoundError
from backend.application.interface.queries.scenario_queries import ScenarioQueries
from backend.application.use_cases.commands.result import CommandReply
from backend.application.use_cases.scenarios.cancel_scenario import CancelScenarioUseCase
from backend.domain.identifiers import ScenarioId, UserId


class CancelScenarioCommandUseCase:
    """Выполняет «отмени сценарий»."""

    def __init__(self, cancel: CancelScenarioUseCase, scenario_queries: ScenarioQueries) -> None:
        """Собирает use case отмены сценария.

        Args:
            cancel: Тот же сценарий, который вызывает интерфейс: фраза лишь
                выбирает, какой именно сценарий имели в виду.
            scenario_queries: Чтения, по которым понимается, какой сценарий имели
                в виду.
        """
        self._cancel = cancel
        self._queries = scenario_queries

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.CANCEL_SCENARIO

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Отдаёт самый свежий сценарий, ещё держащий приоритет.

        «Тот сценарий, который я имел в виду» — заказанный последним, и этот выбор
        делает читающая сторона, а не первый попавшийся элемент списка.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Отменённый сценарий.

        Raises:
            ScenarioNotFoundError: Когда отменять нечего.
        """
        del parsed
        target = await self._queries.latest_holding_priority(user_id)
        if target is None:
            raise ScenarioNotFoundError(ScenarioId.generate())
        view = await self._cancel.execute(user_id, ScenarioId.parse(target.id))
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"scenario_id": str(view.id), "status": view.status.value},
        )
