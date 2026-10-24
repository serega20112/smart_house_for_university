"""Фасад реле поверх транспорта платы.

:class:`BoardGatewayAdapter` — тонкий фасад над одним WebSocket-соединением, чтобы
прикладному слою не приходилось импортировать модуль транспорта.
"""

from __future__ import annotations

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.application.interface.services.board_gateway import BoardGateway
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.esp.connection import EspConnection


class BoardGatewayAdapter(BoardGateway):
    """Водит каналами реле плат через соединение с платами.

    Attributes:
        connection: Соединение с платами на уровне транспорта.
    """

    def __init__(self, connection: EspConnection) -> None:
        """Инициализирует адаптер.

        Args:
            connection: Соединение с платами на уровне транспорта.
        """
        self._connection = connection

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
        accepted, reason = await self._connection.set_relay(user_id, board_id, channel, energized)
        return BoardCommandResult(accepted=accepted, reason=reason)

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
        accepted, reason = await self._connection.set_network(user_id, board_id, profile)
        return BoardCommandResult(accepted=accepted, reason=reason)

    def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Сообщает, держит ли плата соединение сейчас.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            bool: True, когда плата подключена в этот момент.
        """
        return self._connection.is_connected(user_id, board_id)

    def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Возвращает единственную подключённую плату аккаунта.

        Args:
            user_id: Владелец плат.

        Returns:
            EspDeviceId | None: Идентификатор платы, которой приказывать, или None,
            когда у аккаунта не ровно одна подключённая плата.
        """
        return self._connection.board_for(user_id)
