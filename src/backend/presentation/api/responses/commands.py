"""Ответ на высказанную команду."""

from __future__ import annotations

from pydantic import Field

from backend.application.use_cases.commands.result import CommandReply
from backend.presentation.api.responses.common import StrictModel


class CommandResponse(StrictModel):
    """То, что дало выполнение команды.

    Attributes:
        intent: Выполненное намерение или None.
        answer: Фраза, описывающая случившееся.
        message: Та же фраза под именем, которое читают старые клиенты.
        details: Машиночитаемые дополнения.
    """

    intent: str | None
    answer: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


def command_of(reply: CommandReply, answer: str) -> CommandResponse:
    """Возвращает тело ответа на команду.

    Args:
        reply: Результат, собранный прикладным слоем.
        answer: Фраза, которую подобрал составитель ответа.

    Returns:
        CommandResponse: Тело ответа.
    """
    return CommandResponse(
        intent=None if reply.intent is None else reply.intent.value,
        answer=answer,
        message=answer,
        details=reply.details,
    )
