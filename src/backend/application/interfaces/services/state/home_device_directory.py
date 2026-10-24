"""Дешёвое чтение настроенных устройств дома.

Синхронизатору состояния нужно превратить номер реле в устройство, чтобы
сообщение содержало имя, а не канал. Лезть за этим в репозиторий означало бы
открывать транзакцию на каждое сообщение платы, поэтому каталог — именно дешёвое
чтение.
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import UserId


class HomeDeviceDirectory(Protocol):
    """Дешёвые чтения конфигурации устройств одного дома."""

    async def all_of(self, user_id: UserId) -> list[Device]:
        """Все устройства дома."""

    async def by_channel(self, user_id: UserId) -> dict[int, Device]:
        """Устройства дома, проиндексированные по каналу реле."""
