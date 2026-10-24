"""Шлюз к железу: управление каналами реле."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile


class BoardGateway(ABC):
    """Управляет релевыми каналами плат."""

    @abstractmethod
    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Переключает реле и ждёт подтверждения."""

    @abstractmethod
    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Просит плату заново сообщить всё известное ей."""

    @abstractmethod
    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        """Сообщает плате сеть, которую та должна использовать."""

    @abstractmethod
    async def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Подключена ли плата прямо сейчас."""

    @abstractmethod
    async def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Плата, которой адресовать команду дома с одной подключённой платой."""
