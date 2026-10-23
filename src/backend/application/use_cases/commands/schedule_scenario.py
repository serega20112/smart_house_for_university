"""Отложить действие дома на названное время."""

from __future__ import annotations

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.dto.scenario.schedule_scenario_command import ScheduleScenarioCommand
from backend.application.errors import CommandNotUnderstoodError
from backend.application.use_cases.commands.result import CommandReply
from backend.application.use_cases.scenarios.schedule_scenario import ScheduleScenarioUseCase
from backend.domain.identifiers import UserId
from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction


class ScheduleScenarioCommandUseCase:
    """Выполняет «через полчаса сделай двадцать градусов»."""

    def __init__(self, schedule: ScheduleScenarioUseCase, demands: DemandCalculator) -> None:
        """Собирает use case отложенного действия.

        Args:
            schedule: Тот же сценарий, который вызывает интерфейс: фраза лишь
                переводится в команду.
            demands: Модель, решающая, какая способность ведёт к цели.
        """
        self._schedule = schedule
        self._demands = demands

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.SCHEDULE_SCENARIO

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Ставит сценарий, ожидающий своего момента.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Поставленный сценарий.

        Raises:
            CommandNotUnderstoodError: Когда не выводится ни способность, ни цель.
        """
        capability = parsed.capability or self._capability_from_target(parsed)
        if capability is None:
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_CAPABILITY)
        action = ScenarioAction(capability=capability, target_temperature=parsed.temperature)
        view = await self._schedule.execute(
            user_id,
            ScheduleScenarioCommand(
                action=action,
                delay_minutes=parsed.delay_minutes,
                target=parsed.target,
                duration_minutes=parsed.delay_minutes,
            ),
        )
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"scenario_id": str(view.id), "start_at": view.start_at.isoformat()},
        )

    def _capability_from_target(self, parsed: CommandUnderstanding) -> Capability | None:
        if parsed.temperature is None:
            return None
        return self._demands.capability_towards(parsed.temperature.celsius, None)
