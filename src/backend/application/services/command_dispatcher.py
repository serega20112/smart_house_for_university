"""Шина команд: по обработчику на намерение, без божественного объекта.

Шина — единственное место, знающее, какой обработчик служит какому намерению. Добавить
новый оборот, который человек может сказать, значит добавить один обработчик и одну
строку в реестре; это никогда не значит править класс, который уже знает про каждое
действие системы.

Обработчики получают владельца и то, что понял конвейер, и говорят с сервисами, а не
друг с другом. Это и удерживает границу между двумя сценариями от растворения в
цепочке вызовов, где транзакцию не сыскать.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.errors import CommandNotUnderstoodError
from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.identifiers import UserId

CommandHandler = Callable[[UserId, CommandUnderstanding], Awaitable[CommandReply]]


class CommandDispatcher:
    """Понимает написанное предложение и направляет его нужному обработчику."""

    def __init__(
        self,
        understanding: CommandUnderstandingPort,
        handlers: dict[Intent, CommandHandler],
    ) -> None:
        """Инициализирует раздатчик.

        Args:
            understanding: Конвейер, превращающий предложение в структурированную команду.
            handlers: Обработчик каждого намерения, которое можно выполнить.
        """
        self._understanding = understanding
        self._handlers = handlers

    async def dispatch(self, user_id: UserId, text: str) -> CommandReply:
        """Понимает предложение и выполняет то, о чём в нём просят.

        Args:
            user_id: Владелец, для которого выполняют команду.
            text: Предложение таким, каким интерфейс его получил.

        Returns:
            CommandReply: То, что дало выполнение команды.

        Raises:
            CommandNotUnderstoodError: Когда предложение нельзя выполнить как оно есть.
            Причина идёт вместе с отказом, чтобы интерфейс задал ровно тот уточняющий
            вопрос, который нужен.
        """
        parsed = await self._understanding.understand(text)
        if parsed.intent is None:
            raise CommandNotUnderstoodError(ClarificationReason.UNRECOGNIZED_INTENT)
        if not await self._understanding.is_confident_enough(parsed):
            raise CommandNotUnderstoodError(
                ClarificationReason.LOW_CONFIDENCE, confidence=parsed.confidence
            )
        handler = self._handlers.get(parsed.intent)
        if handler is None:
            raise CommandNotUnderstoodError(ClarificationReason.UNRECOGNIZED_INTENT)
        return await handler(user_id, parsed)
