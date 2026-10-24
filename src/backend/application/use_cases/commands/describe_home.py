"""Рассказать, что сейчас делает дом."""

from __future__ import annotations

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.services.home_overview import HomeOverviewQuery
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.identifiers import UserId


class DescribeHomeCommandUseCase:
    """Выполняет «какое состояние дома»."""

    def __init__(self, overview: HomeOverviewQuery) -> None:
        """Собирает use case описания дома.

        Args:
            overview: Единый сборщик читающей проекции дома — тот же, что питает экран,
                поэтому слово и картинка не расходятся в том, что они понимают под
                «состоянием дома».
        """
        self._overview = overview

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.DESCRIBE_HOME

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Описывает живое состояние дома.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: То, что дом делает прямо сейчас.
        """
        del parsed
        view = await self._overview.load(user_id)
        return CommandReply(
            intent=self.intent,
            answer="",
            details={
                "board_online": view.board_online,
                "automation_suspended": view.automation_suspended,
                "temperature": view.reading.temperature,
                "humidity": view.reading.humidity,
                "devices_on": [device.name for device in view.devices if device.status.is_active],
                "automation_enabled": view.automation.enabled,
                "active_scenarios": [str(scenario.id) for scenario in view.active_scenarios],
            },
        )
