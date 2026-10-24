"""Дешёвое чтение настроенных устройств дома.

Синхронизатору состояния нужно превратить номер реле в устройство, чтобы
сообщение содержало имя, а не канал. Лезть за этим в репозиторий означало бы
открывать транзакцию на каждое сообщение платы, поэтому каталог — именно дешёвое
чтение.
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import EspDeviceId, UserId


class HomeDeviceDirectory(Protocol):
    """Дешёвые чтения конфигурации устройств одного дома."""

    async def all_of(self, user_id: UserId) -> list[Device]:
        """Все устройства дома."""

    async def by_channel(self, user_id: UserId, board_id: EspDeviceId) -> dict[int, Device]:
        """Устройства одной платы, проиндексированные по каналу реле.

        Каналы двух плат совпадают по номерам, но означают разные контакты,
        поэтому индекс строится только по устройствам этой платы.
        """
