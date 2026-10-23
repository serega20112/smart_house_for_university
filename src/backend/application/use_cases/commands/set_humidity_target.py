"""Задать целевую влажность дома."""

from __future__ import annotations

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import CommandNotUnderstoodError
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import UserId
from backend.domain.value_objects.climate.humidity import Humidity


class SetHumidityTargetCommandUseCase:
    """Выполняет «шестьдесят процентов влажности»."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Собирает use case цели по влажности.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
        """
        self._home_uow = home_uow

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.SET_HUMIDITY

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Сохраняет влажность, которую попросил человек.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Сохранённая цель.

        Raises:
            CommandNotUnderstoodError: Когда во фразе нет значения влажности.
            InvalidHumidityError: Когда значение вне нуля — ста процентов.
        """
        if parsed.humidity is None:
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_HUMIDITY)
        target = Humidity(parsed.humidity)
        async with self._home_uow() as uow:
            stored = await uow.automation.get(user_id)
            settings = stored if stored is not None else AutomationSettings.create(user_id)
            settings.aim_at_humidity(target)
            await uow.automation.save(settings)
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"humidity": target.percent},
        )
