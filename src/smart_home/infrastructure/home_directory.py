"""Cheap reads of the device configuration of one home.

A board reports its relays several times a second. Turning every relay change
into a transaction would spend the connection pool on hardware chatter, so this
adapter answers straight from the engine with plain selects: no unit of work is
opened and no aggregate is rebuilt beyond what the reader actually needs.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from smart_home.application.ports.home import HomeDeviceDirectory
from smart_home.domain.devices.device import Device
from smart_home.domain.identifiers import UserId
from smart_home.infrastructure.database import mappers
from smart_home.infrastructure.database.repositories import capabilities_of, every_row
from smart_home.infrastructure.database.tables import DeviceRow


class SqlHomeDeviceDirectory(HomeDeviceDirectory):
    """Reads of the devices of one home, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the directory.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def all_of(self, user_id: UserId) -> list[Device]:
        """Return every device of a home.

        Args:
            user_id: Owner of the home.

        Returns:
            list[Device]: Configured devices.
        """
        async with self._engine.connect() as connection:
            rows = await every_row(connection, DeviceRow, DeviceRow.user_id == user_id.value)
            stored = await capabilities_of(connection, [row.id for row in rows])
        return [mappers.device_from_row(row, stored.get(row.id, frozenset())) for row in rows]

    async def by_channel(self, user_id: UserId) -> dict[int, Device]:
        """Return the devices of a home indexed by their relay channel.

        Args:
            user_id: Owner of the home.

        Returns:
            dict[int, Device]: Devices mapped to their channel. A channel with no
            device behind it is simply absent.
        """
        devices = await self.all_of(user_id)
        return {int(device.channel): device for device in devices}
