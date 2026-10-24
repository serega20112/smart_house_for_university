"""Сообщения, которые плата приносит во время соединения.

Транспорт превращает кадр в одно из этих значений и больше ничего не решает: что
означает пришедшее для дома, знает прикладной слой.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.value_objects.climate.climate_reading import ClimateReading


@dataclass(frozen=True, slots=True)
class BoardStateReport:
    """Всё, что плата знает: положения контактов и показания датчиков.

    Attributes:
        relays: Положения каналов по порядку, начиная с первого.
        reading: Показания климата; пустой снимок, когда датчик молчит.
    """

    relays: list[bool] = field(default_factory=list)
    reading: ClimateReading = field(default_factory=ClimateReading)


@dataclass(frozen=True, slots=True)
class BoardTelemetry:
    """Периодические показания датчиков без состояния реле."""

    reading: ClimateReading


@dataclass(frozen=True, slots=True)
class BoardAck:
    """Подтверждение одной команды."""

    command_id: str


@dataclass(frozen=True, slots=True)
class BoardFailure:
    """Отказ, о котором сообщила сама плата."""

    code: str
    message: str = ""


@dataclass(frozen=True, slots=True)
class BoardFrameUnreadable:
    """Кадр не прочитан: сокет жив, а понятного сообщения нет."""

    reason: str


BoardMessage = BoardStateReport | BoardTelemetry | BoardAck | BoardFailure | BoardFrameUnreadable
