"""Что делать с сообщением, которое плата принесла в соединении.

Транспорт только превращает кадр в значение из `dto/boards`, а здесь решение, кого
оно касается: положение каналов и показания климата идут в состояние дома, отказ
платы — в тот же приёмник отдельным событием, а неподтверждённый кадр остаётся
механикой соединения и до прикладного слоя не доходит.
"""

from __future__ import annotations

from backend.application.dto.boards.board_message import (
    BoardFailure,
    BoardFrameUnreadable,
    BoardMessage,
    BoardStateReport,
    BoardTelemetry,
)
from backend.application.interfaces.services.boards.board_report import BoardReport
from backend.domain.identifiers import EspDeviceId, UserId

UNREADABLE_CODE = "BAD_MESSAGE"


class RouteBoardMessageUseCase:
    """Разкладывает сообщение платы по приёмнику состояния дома.

    Args:
        report: Приёмник, которому уходят сообщения всех плат.
    """

    def __init__(self, report: BoardReport) -> None:
        """Инициализирует разбор сообщений."""
        self._report = report

    async def execute(self, user_id: UserId, board_id: EspDeviceId, message: BoardMessage) -> None:
        """Сообщает дому всё, что плата принесла в этом кадре.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            message: Прочитанное сообщение.
        """
        match message:
            case BoardStateReport(relays=relays, reading=reading):
                if relays:
                    await self._report.on_relay_states(user_id, board_id, list(relays))
                await self._report.on_reading(user_id, board_id, reading)
            case BoardTelemetry(reading=reading):
                await self._report.on_reading(user_id, board_id, reading)
            case BoardFailure(code=code, message=text):
                await self._report.on_error(user_id, board_id, code, text)
            case BoardFrameUnreadable(reason=reason):
                await self._report.on_error(user_id, board_id, UNREADABLE_CODE, reason)
