"""Рассказать, что сейчас делает дом."""

from __future__ import annotations

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.interface.queries.automation_queries import AutomationQueries
from backend.application.interface.queries.device_queries import DeviceQueries
from backend.application.interface.queries.scenario_queries import ScenarioQueries
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.identifiers import UserId


class DescribeHomeCommandUseCase:
    """Выполняет «какое состояние дома»."""

    def __init__(
        self,
        state_store: HomeStateStore,
        device_queries: DeviceQueries,
        scenario_queries: ScenarioQueries,
        automation_queries: AutomationQueries,
        clock: Clock,
    ) -> None:
        """Собирает use case описания дома.

        Args:
            state_store: Хранилище изменчивого состояния дома.
            device_queries: Чтения конфигурации устройств.
            scenario_queries: Чтения сценариев.
            automation_queries: Чтения настроек автоматизации.
            clock: Источник текущего момента.
        """
        self._state_store = state_store
        self._devices = device_queries
        self._scenarios = scenario_queries
        self._automation = automation_queries
        self._clock = clock

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.DESCRIBE_HOME

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Описывает живое состояние дома.

        Показания берутся из хранилища состояния, а не из полного снимка дома:
        вопрос про одну цифру не должен тянуть за собой весь дом.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: То, что дом делает прямо сейчас.
        """
        del parsed
        state = await self._state_store.read(user_id)
        devices = await self._devices.list_all(user_id)
        scenarios = await self._scenarios.list_holding_priority(user_id)
        automation = await self._automation.get(user_id)
        measured = state.reading.temperature
        return CommandReply(
            intent=self.intent,
            answer="",
            details={
                "board_online": state.board_online,
                "automation_suspended": state.is_automation_suspended(self._clock.now()),
                "temperature": None if measured is None else measured.celsius,
                "humidity": (
                    None if state.reading.humidity is None else state.reading.humidity.percent
                ),
                "devices_on": [device.name for device in devices if device.status.is_active],
                "automation_enabled": automation.enabled,
                "active_scenarios": [str(scenario.id) for scenario in scenarios],
            },
        )
