"""Дешёвые чтения настройки устройств одного дома.

Плата сообщает положения реле несколько раз в секунду. Превращать каждое такое
сообщение в транзакцию значило бы тратить пул соединений на шум железа, поэтому
этот адаптер отвечает обычным select'ом через короткую сессию: явная граница
единицы работы не открывается, и агрегат не пересобирается дальше того, что читателю
нужно. Сессия, а не голое соединение, — потому что только она гидратирует ORM-сущности.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.interfaces.services.state.home_device_directory import HomeDeviceDirectory
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.database.mappers.device import device_from_row
from backend.infrastructure.database.models import DeviceModel
from backend.infrastructure.database.repositories.base import every_row
from backend.infrastructure.database.repositories.child_rows import capabilities_of


class SqlHomeDeviceDirectory(HomeDeviceDirectory):
    """Чтения устройств одного дома, отвечаемые без явной транзакции.

    Args:
        session_factory: Фабрика сессий, на которой чтения выполняются.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует справочник дома.

        Args:
            session_factory: Фабрика сессий, из которой читают.
        """
        self._session_factory = session_factory

    async def all_of(self, user_id: UserId) -> list[Device]:
        """Возвращает каждое устройство дома.

        Args:
            user_id: Владелец дома.

        Returns:
            list[Device]: Настроенные устройства.
        """
        async with self._session_factory() as session:
            rows = await every_row(session, DeviceModel, DeviceModel.user_id == user_id.value)
            stored = await capabilities_of(session, [row.id for row in rows])
        return [device_from_row(row, stored.get(row.id, frozenset())) for row in rows]

    async def by_channel(self, user_id: UserId, board_id: EspDeviceId) -> dict[int, Device]:
        """Возвращает устройства одной платы, выставленные по каналу реле.

        Args:
            user_id: Владелец дома.
            board_id: Плата, чьи каналы только что сообщили положения.

        Returns:
            dict[int, Device]: Устройства этой платы по их каналу. Канал без
            устройства за собой просто отсутствует.
        """
        devices = await self.all_of(user_id)
        return {int(device.channel): device for device in devices if device.board_id == board_id}
