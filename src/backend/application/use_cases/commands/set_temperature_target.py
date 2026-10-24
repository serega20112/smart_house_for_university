"""Задать целевую температуру дома."""

from __future__ import annotations

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import CommandNotUnderstoodError
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import UserId


class SetTemperatureTargetCommandUseCase:
    """Выполняет «сделай двадцать градусов»."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает use case цели по температуре.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
        """
        self._home_uow = home_uow

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.SET_TEMPERATURE

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Сохраняет температуру, которую попросил человек.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Сохранённая цель.

        Raises:
            CommandNotUnderstoodError: Когда во фразе нет значения температуры.
            InvalidTemperatureError: Когда значение физически невозможно.
        """
        if parsed.temperature is None:
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_TEMPERATURE)
        async with self._home_uow() as uow:
            stored = await uow.automation.get(user_id)
            settings = stored if stored is not None else AutomationSettings.create(user_id)
            settings.aim_at_temperature(parsed.temperature)
            await uow.automation.save(settings)
            await uow.commit()
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"temperature": parsed.temperature.celsius},
        )
