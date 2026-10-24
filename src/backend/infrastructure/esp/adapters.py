"""Фасад реле поверх транспорта платы.

:class:`BoardGatewayAdapter` — тонкий фасад над одним WebSocket-соединением, чтобы
прикладному слою не приходилось импортировать модуль транспорта.
"""

from __future__ import annotations

import time

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.system import metrics


class BoardGatewayAdapter(BoardGateway):
    """Водит каналами реле плат через соединение с этим процессом.

    Переключение и смена сети идут прямо в транспорт, держящий WebSocket, а доступность
    читается из общего реестра присутствия: решение «какой платой командовать» должно
    видеть то же, что и рабочий, а не только словарь этого процесса.

    Attributes:
        connection: Соединение с платами на уровне транспорта.
        presence: Разделённый между процессами реестр подключённых плат.
    """

    def __init__(self, connection: EspConnection, presence: RedisBoardPresence) -> None:
        """Инициализирует адаптер.

        Args:
            connection: Соединение с платами на уровне транспорта.
            presence: Разделённый между процессами реестр подключённых плат.
        """
        self._connection = connection
        self._presence = presence

    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Переключает реле и ждёт подтверждения.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            channel: Физический канал реле.
            energized: True замкнуть контакт, False разомкнуть.

        Returns:
            BoardCommandResult: Ответ платы.
        """
        started = time.perf_counter()
        result = await self._connection.set_relay(user_id, board_id, channel, energized)
        metrics.record_board_command(result.outcome, time.perf_counter() - started)
        return result

    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Просит плату прислать заново всё, что она знает.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        await self._connection.request_state(user_id, board_id)

    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        """Сообщает плате сеть, которую та должна использовать.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            profile: Сеть, которую должна использовать плата.

        Returns:
            BoardCommandResult: Ответ платы.
        """
        return await self._connection.set_network(user_id, board_id, profile)

    async def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Сообщает, держит ли плата соединение сейчас.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            bool: True, когда плата подключена в этот момент.
        """
        return await self._presence.is_connected(user_id, board_id)

    async def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Возвращает единственную подключённую плату аккаунта.

        Args:
            user_id: Владелец плат.

        Returns:
            EspDeviceId | None: Идентификатор платы, которой приказывать, или None,
            когда у аккаунта не ровно одна подключённая плата.
        """
        return await self._presence.board_for(user_id)
