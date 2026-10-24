"""Дешёвые чтения настройки устройств одного дома.

Плата сообщает положения реле несколько раз в секунду. Превращать каждое такое
сообщение в транзакцию значило бы тратить пул соединений на шум железа, поэтому
этот адаптер отвечает обычным select'ом прямо из движка: единица работы не
открывается, и агрегат не пересобирается дальше того, что читателю нужно.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.application.interface.services.home_device_directory import HomeDeviceDirectory
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import UserId
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import every_row
from backend.infrastructure.database.repositories.child_rows import capabilities_of
from backend.infrastructure.database.tables import DeviceRow


class SqlHomeDeviceDirectory(HomeDeviceDirectory):
    """Чтения устройств одного дома, отвечаемые без транзакции.

    Args:
        engine: Движок, на котором чтения выполняются.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует справочник дома.

        Args:
            engine: Движок, из которого читают.
        """
        self._engine = engine

    async def all_of(self, user_id: UserId) -> list[Device]:
        """Возвращает каждое устройство дома.

        Args:
            user_id: Владелец дома.

        Returns:
            list[Device]: Настроенные устройства.
        """
        async with self._engine.connect() as connection:
            rows = await every_row(connection, DeviceRow, DeviceRow.user_id == user_id.value)
            stored = await capabilities_of(connection, [row.id for row in rows])
        return [mappers.device_from_row(row, stored.get(row.id, frozenset())) for row in rows]

    async def by_channel(self, user_id: UserId) -> dict[int, Device]:
        """Возвращает устройства дома, выставленные по каналу реле.

        Args:
            user_id: Владелец дома.

        Returns:
            dict[int, Device]: Устройства по их каналу. Канал без устройства за
            собой просто отсутствует.
        """
        devices = await self.all_of(user_id)
        return {int(device.channel): device for device in devices}
