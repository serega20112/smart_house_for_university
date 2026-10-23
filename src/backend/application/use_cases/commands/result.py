"""Результат сценария, к которому привела свободная формулировка."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.application.dto.language.intent import Intent


@dataclass(frozen=True, slots=True)
class CommandReply:
    """Ответ на фразу, которую сдал интерфейс.

    Отказ не живёт внутри значения со статусом: сценарий поднимает исключение, а
    интерфейс его ловит. Здесь остаётся сам ответ.

    Attributes:
        intent: Выполненное намерение или None, если фразу не поняли вовсе.
        answer: Текст, описывающий, что произошло.
        details: Машиночитаемые дополнения — например изменённые устройства.
    """

    intent: Intent | None
    answer: str
    details: dict[str, object] = field(default_factory=dict)
