"""Сказать измеренную температуру."""

from __future__ import annotations

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.identifiers import UserId


class ReadTemperatureCommandUseCase:
    """Выполняет «какая температура»."""

    def __init__(self, state_store: HomeStateStore) -> None:
        """Собирает use case чтения температуры.

        Args:
            state_store: Хранилище изменчивого состояния дома.
        """
        self._state_store = state_store

    @property
    def intent(self) -> Intent:
        """Намерение, которое закрывает этот сценарий."""
        return Intent.READ_TEMPERATURE

    async def execute(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Отдаёт измеренную температуру.

        Args:
            user_id: Владелец, для которого выполняется команда.
            parsed: Что конвейер понял из фразы.

        Returns:
            CommandReply: Измеренная температура.
        """
        del parsed
        state = await self._state_store.read(user_id)
        measured = state.reading.temperature
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"temperature": None if measured is None else measured.celsius},
        )
