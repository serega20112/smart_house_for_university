"""Кодек wire-протокола плат.

Слой транспорта умеет только превращать текст кадра в значения прикладного слоя и
обратно. Всё, что эти значения значат для дома, решает прикладной слой, а здесь нет
ни правил, ни вызовов сервисов.

Нечитаемый кадр остаётся значением `BoardFrameUnreadable`, а не исключением: одна
опечатка в JSON не повод терять дом целиком, и решение о том, что с таким кадром
делать, тоже не здесь.
"""

from __future__ import annotations

from backend.application.dto.boards.board_admission import BoardGreeting
from backend.application.dto.boards.board_message import (
    BoardAck,
    BoardFailure,
    BoardFrameUnreadable,
    BoardMessage,
    BoardStateReport,
    BoardTelemetry,
)
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.infrastructure.esp import protocol


def read_greeting(raw: str) -> BoardGreeting | None:
    """Читает первое сообщение платы.

    Args:
        raw: Текст рамки так, как она пришла.

    Returns:
        BoardGreeting | None: Приветствие платы либо None, когда кадр им не является.
    """
    try:
        frame = protocol.parse_inbound(raw)
    except protocol.MalformedFrameError:
        return None
    if not isinstance(frame, protocol.HelloFrame):
        return None
    return BoardGreeting(
        pairing_key=frame.pairing_key,
        label=frame.label,
        firmware=frame.firmware_version,
        ssid=frame.ssid,
        provisioned=frame.provisioned,
        claims_owned=frame.claim,
    )


def read_message(raw: str) -> BoardMessage:
    """Читает одно сообщение платы внутри установленного соединения.

    Args:
        raw: Текст рамки так, как она пришла.

    Returns:
        BoardMessage: Прочитанное сообщение либо отметка, что прочитать его не удалось.
    """
    try:
        frame = protocol.parse_inbound(raw)
    except protocol.MalformedFrameError as error:
        return BoardFrameUnreadable(reason=str(error))
    match frame:
        case protocol.AckFrame(command_id=command_id):
            return BoardAck(command_id=command_id)
        case protocol.StateFrame(relays=relays):
            return BoardStateReport(relays=list(relays), reading=_reading_of(frame))
        case protocol.SensorDataFrame():
            return BoardTelemetry(reading=_reading_of(frame))
        case protocol.ErrorFrame(code=code, message=message):
            return BoardFailure(code=code, message=message)
        case _:
            return BoardFrameUnreadable(reason="unexpected_frame_type")


def _reading_of(frame: protocol.StateFrame | protocol.SensorDataFrame) -> ClimateReading:
    """Переводит сырые числа датчика в снимок климата; молчание остаётся пустым снимком."""
    return ClimateReading.measured(frame.temperature, frame.humidity)
