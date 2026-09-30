"""SQLAlchemy implementation of the device repository port."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_home_backend.application.interface.repositories import DeviceRepository
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.infrastructure.database import mappers
from smart_home_backend.infrastructure.database.models import DeviceRow


class SqlDeviceRepository(DeviceRepository):
    """Reads and writes devices through an async SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session owned by the current unit of work.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self) -> Sequence[Device]:
        """Return every configured device ordered by id.

        Returns:
            Sequence[Device]: Configured devices.
        """
        result = await self._session.execute(select(DeviceRow).order_by(DeviceRow.id))
        return [mappers.device_from_row(row) for row in result.scalars().all()]

    async def get(self, device_id: int) -> Device | None:
        """Return a device by id.

        Args:
            device_id: Identifier of the device.

        Returns:
            Device | None: Device or None when it does not exist.
        """
        row = await self._session.get(DeviceRow, device_id)
        return mappers.device_from_row(row) if row else None

    async def get_by_channel(self, channel: int) -> Device | None:
        """Return the device bound to a physical relay channel.

        Args:
            channel: Physical relay channel.

        Returns:
            Device | None: Device or None when the channel is unassigned.
        """
        result = await self._session.execute(
            select(DeviceRow).where(DeviceRow.physical_channel == channel)
        )
        row = result.scalars().first()
        return mappers.device_from_row(row) if row else None

    async def save(self, device: Device) -> Device:
        """Create or update a device.

        Args:
            device: Device to persist.

        Returns:
            Device: Persisted device including its identifier.
        """
        row = await self._session.get(DeviceRow, device.id) if device.id else None
        if row is None:
            row = mappers.device_to_row(device)
            self._session.add(row)
            await self._session.flush()
            device.id = row.id
            return device

        row.name = device.name
        row.type = device.type.value
        row.physical_channel = device.physical_channel
        row.capabilities = sorted(capability.value for capability in device.capabilities)
        row.enabled = device.enabled
        row.automation_enabled = device.automation_enabled
        await self._session.flush()
        return device

    async def delete(self, device_id: int) -> bool:
        """Delete a device.

        Args:
            device_id: Identifier of the device.

        Returns:
            bool: True when a device was removed.
        """
        row = await self._session.get(DeviceRow, device_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def channel_in_use(self, channel: int, exclude_id: int | None = None) -> bool:
        """Return whether a physical channel is already taken.

        Args:
            channel: Physical relay channel.
            exclude_id: Device that is allowed to keep the channel.

        Returns:
            bool: True when another device already uses the channel.
        """
        statement = select(DeviceRow.id).where(DeviceRow.physical_channel == channel)
        if exclude_id is not None:
            statement = statement.where(DeviceRow.id != exclude_id)
        result = await self._session.execute(statement.limit(1))
        return result.scalars().first() is not None
