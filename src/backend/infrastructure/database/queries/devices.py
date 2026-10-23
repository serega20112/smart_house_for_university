"""Чтения настройки устройств.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.infrastructure.database.repositories.base import every_row, first_row
from backend.infrastructure.database.repositories.child_rows import (
    capabilities_of,
)
from backend.infrastructure.database.tables import (
    DeviceRow,
)


class SqlDeviceQueries:
    """Reads of the device configuration, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[DeviceView]:
        """Return every device of an account.

        Args:
            user_id: Owner of the devices.

        Returns:
            list[DeviceView]: Devices shaped for display.
        """
        async with self._engine.connect() as connection:
            rows = await every_row(connection, DeviceRow, DeviceRow.user_id == user_id.value)
            stored = await capabilities_of(connection, [row.id for row in rows])
        return [device_view_of(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> DeviceView | None:
        """Return one device of an account.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            DeviceView | None: Device, or None when the account has no such one.
        """
        async with self._engine.connect() as connection:
            row = await first_row(
                connection,
                DeviceRow,
                DeviceRow.id == device_id.value,
                DeviceRow.user_id == user_id.value,
            )
            if row is None:
                return None
            stored = await capabilities_of(connection, [row.id])
        return device_view_of(row, stored.get(row.id, frozenset()))


def device_view_of(row: DeviceRow, capabilities: frozenset[Capability]) -> DeviceView:
    """Return the read model of one stored device.

    The device is reported as off because its logical state belongs to the live
    layer of the hardware, not to a table row.

    Args:
        row: Row to shape.
        capabilities: Capabilities read from the capability table.

    Returns:
        DeviceView: Device shaped for display.
    """
    return DeviceView(
        id=DeviceId.parse(row.id),
        name=row.name,
        kind=DeviceKind.parse(row.kind),
        channel=row.channel,
        capabilities=capabilities,
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
        status=DeviceStatus.OFF,
    )
