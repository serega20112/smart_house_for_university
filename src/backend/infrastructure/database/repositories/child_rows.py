"""Дочерние строки, которые читаются пачкой вместе с родителем."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.domain.value_objects.devices.capability import Capability
from backend.infrastructure.database.tables import (
    AutomationParticipantRow,
    DeviceCapabilityRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


async def capabilities_of(
    runner: Runner, device_ids: Sequence[UUID]
) -> dict[UUID, frozenset[Capability]]:
    """Return the capabilities of every device of a lookup.

    Args:
        runner: Session or connection the lookup runs on.
        device_ids: Devices the caller is about to return.

    Returns:
        dict[UUID, frozenset[Capability]]: Capabilities grouped by device.
    """
    if not device_ids:
        return {}
    result = await runner.execute(
        select(DeviceCapabilityRow.device_id, DeviceCapabilityRow.capability).where(
            DeviceCapabilityRow.device_id.in_(device_ids)
        )
    )
    grouped: dict[UUID, set[Capability]] = {}
    for device_id, capability in result.all():
        grouped.setdefault(device_id, set()).add(Capability.parse(capability))
    return {device_id: frozenset(values) for device_id, values in grouped.items()}


async def participants_of(runner: Runner, user_id: UserId) -> frozenset[DeviceId]:
    """Return the devices automation is allowed to drive.

    Args:
        runner: Session or connection the lookup runs on.
        user_id: Owner of the configuration.

    Returns:
        frozenset[DeviceId]: Participating devices, empty for every opted in one.
    """
    result = await runner.execute(
        select(AutomationParticipantRow.device_id).where(
            AutomationParticipantRow.user_id == user_id.value
        )
    )
    return frozenset(DeviceId.parse(value) for value in result.scalars().all())
