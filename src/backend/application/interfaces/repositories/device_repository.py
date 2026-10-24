"""Хранилище логических устройств одного аккаунта.

Каждая операция ограничена владельцем, поэтому вызывающий не может достать чужое
устройство, даже угадав его идентификатор.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence

from backend.application.interfaces.repositories.base import CrudRepository
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId


class DeviceRepository(CrudRepository[Device, DeviceId]):
    """Полный набор операций над устройствами аккаунта.

    Кроме обычного набора здесь живут две операции, привязанные к плате: именно
    ими решается судьба устройств, когда плата уходит из дома.
    """

    @abstractmethod
    async def list_for_board(self, user_id: UserId, board_id: EspDeviceId) -> Sequence[Device]:
        """Возвращает устройства, стоящие на каналах одной платы.

        Args:
            user_id: Владелец устройств.
            board_id: Плата, каналы которой интересуют вызывающего.

        Returns:
            Sequence[Device]: Устройства этой платы в порядке каналов.
        """

    @abstractmethod
    async def delete_for_board(self, user_id: UserId, board_id: EspDeviceId) -> int:
        """Удаляет все устройства одной платы, возвращая их число.

        Args:
            user_id: Владелец устройств.
            board_id: Плата, устройства которой удаляют.

        Returns:
            int: Сколько устройств удалили.
        """
