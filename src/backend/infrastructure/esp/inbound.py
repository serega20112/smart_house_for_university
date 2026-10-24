"""Превращение входящего кадра в сообщение приёмнику состояния дома.

Здесь всё, что плата сообщила о себе, переводится с языка протокола на вызовы
единственного потребителя — приёмника состояния. Ни одного решения о доме тут не
принимается: переводчик не выбирает устройства и не трогает автоматизацию.
"""

from __future__ import annotations

from backend.application.interface.services.board_report import BoardReport
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.infrastructure.esp import protocol
from backend.infrastructure.esp.session import BoardSession
from backend.infrastructure.logging import get_logger

log = get_logger("esp.inbound")

BAD_MESSAGE_CODE = "BAD_MESSAGE"


async def read(session: BoardSession, raw: str, report: BoardReport) -> None:
    """Разбирает одну рамку соединения и передаёт её содержание приёмнику.

    Кривой кадр не рвёт соединение: плата получает отказ по существу, а её сеанс
    остаётся, потому что одна опечатка в JSON не повод терять дом целиком.

    Args:
        session: Сеанс платы, приславшей рамку.
        raw: Текст рамки так, как она пришла.
        report: Приёмник состояния дома.
    """
    try:
        frame = protocol.parse_inbound(raw)
    except protocol.MalformedFrameError as error:
        log.warning(
            "esp.frame_malformed",
            user=str(session.user_id),
            board=str(session.board_id),
            error=str(error),
        )
        await report.on_error(session.user_id, session.board_id, BAD_MESSAGE_CODE, str(error))
        return
    await apply(session, frame, report)


async def apply(session: BoardSession, frame: protocol.InboundFrame, report: BoardReport) -> None:
    """Отдаёт разобранный кадр тому, кого он касается.

    Args:
        session: Сеанс платы, приславшей кадр.
        frame: Разобранный кадр протокола.
        report: Приёмник состояния дома.
    """
    match frame:
        case protocol.HelloFrame():
            log.info(
                "esp.board_hello",
                user=str(session.user_id),
                board=str(session.board_id),
                firmware=frame.firmware_version,
            )
        case protocol.AckFrame():
            session.resolve_ack(frame.command_id)
        case protocol.ErrorFrame():
            await report.on_error(session.user_id, session.board_id, frame.code, frame.message)
        case protocol.StateFrame():
            if frame.relays:
                await report.on_relay_states(session.user_id, session.board_id, list(frame.relays))
            await report.on_reading(
                session.user_id,
                session.board_id,
                ClimateReading.measured(frame.temperature, frame.humidity),
            )
        case protocol.SensorDataFrame():
            await report.on_reading(
                session.user_id,
                session.board_id,
                ClimateReading.measured(frame.temperature, frame.humidity),
            )
