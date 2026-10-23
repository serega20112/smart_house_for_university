"""Хранилище логических устройств PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    ConcurrentModificationError,
)
from backend.domain.aggregates.device.device import Device
from backend.domain.exceptions import ChannelConflictError
from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import (
    every_row,
    first_row,
    insert_rows,
    is_unique_violation,
)
from backend.infrastructure.database.repositories.child_rows import capabilities_of
from backend.infrastructure.database.tables import (
    DeviceCapabilityRow,
    DeviceRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlDeviceRepository:
    """Storage of the logical devices of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self, user_id: UserId) -> Sequence[Device]:
        """Return every device of an account.

        Args:
            user_id: Owner of the devices.

        Returns:
            Sequence[Device]: Configured devices.
        """
        rows = await every_row(self._session, DeviceRow, DeviceRow.user_id == user_id.value)
        stored = await capabilities_of(self._session, [row.id for row in rows])
        return [mappers.device_from_row(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> Device | None:
        """Return one device of an account.

        The lookup is scoped to the owner, so a device of another account reads as
        missing instead of being handed out.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            Device | None: Device, or None when the account has no such one.
        """
        row = await first_row(
            self._session,
            DeviceRow,
            DeviceRow.id == device_id.value,
            DeviceRow.user_id == user_id.value,
        )
        if row is None:
            return None
        stored = await capabilities_of(self._session, [row.id])
        return mappers.device_from_row(row, stored.get(row.id, frozenset()))

    async def add(self, device: Device) -> None:
        """Store a newly created device.

        The row of the device is written before its capabilities, because every
        capability row carries a foreign key to it. The channel a device is
        wired to is unique per account, so the store refuses the second claim
        instead of a lookup deciding it a moment earlier.

        Args:
            device: Device to persist.

        Returns:
            None.

        Raises:
            ChannelConflictError: When the channel is already wired to another
            device of the same account.
        """
        values = mappers.row_values(DeviceRow.__table__, mappers.device_to_row(device))
        try:
            await self._session.execute(insert(DeviceRow.__table__).values(**values))
            await insert_rows(
                self._session, DeviceCapabilityRow.__table__, mappers.capability_rows(device)
            )
            await self._session.flush()
        except IntegrityError as error:
            if not is_unique_violation(error):
                raise
            raise ChannelConflictError(int(device.channel)) from error

    async def update(self, device: Device) -> None:
        """Store a changed device under a revision it has actually seen.

        The statement carries the revision the aggregate was read at: the store
        updates nothing when somebody changed the row meanwhile. The capabilities
        are replaced rather than merged: the aggregate holds the complete set,
        so a capability that is no longer listed was removed on purpose.

        Args:
            device: Device to persist.

        Returns:
            None.

        Raises:
            ConcurrentModificationError: When the row moved on since it was read.
            ChannelConflictError: When the new channel is already wired to
            another device of the same account.
        """
        row = mappers.device_to_row(device)
        try:
            result = await self._session.execute(
                update(DeviceRow)
                .where(
                    DeviceRow.id == device.id.value,
                    DeviceRow.user_id == device.user_id.value,
                    DeviceRow.version == device.version,
                )
                .values(
                    name=row.name,
                    kind=row.kind,
                    channel=row.channel,
                    enabled=row.enabled,
                    automation_enabled=row.automation_enabled,
                    version=device.version + 1,
                )
            )
            await self._session.flush()
        except IntegrityError as error:
            if not is_unique_violation(error):
                raise
            raise ChannelConflictError(int(device.channel)) from error
        if not result.rowcount:
            raise ConcurrentModificationError("device", device.id)
        device.version += 1
        await self._session.execute(
            delete(DeviceCapabilityRow).where(DeviceCapabilityRow.device_id == device.id.value)
        )
        await insert_rows(
            self._session, DeviceCapabilityRow.__table__, mappers.capability_rows(device)
        )
        await self._session.flush()

    async def delete(self, user_id: UserId, device_id: DeviceId) -> bool:
        """Remove a device of an account.

        The capabilities, the automation participations and the dashboard entries
        pointing at the device are removed by the cascading foreign keys of the
        store, so no row survives describing something that no longer exists.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            bool: True when a device was removed.
        """
        result = await self._session.execute(
            delete(DeviceRow).where(
                DeviceRow.id == device_id.value, DeviceRow.user_id == user_id.value
            )
        )
        return bool(result.rowcount)
