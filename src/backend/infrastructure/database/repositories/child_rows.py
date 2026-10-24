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
    """Возвращает способности всякого устройства из выборки.

    Args:
        runner: Сессия или соединение, на котором идёт выборка.
        device_ids: Устройства, которые вызывающий собирается вернуть.

    Returns:
        dict[UUID, frozenset[Capability]]: Способности, разложенные по устройствам.
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
    """Возвращает устройства, которыми автоматизации разрешено управлять.

    Args:
        runner: Сессия или соединение, на котором идёт выборка.
        user_id: Владелец настройки.

    Returns:
        frozenset[DeviceId]: Участвующие устройства; пусто — значит «каждое
        согласившееся».
    """
    result = await runner.execute(
        select(AutomationParticipantRow.device_id).where(
            AutomationParticipantRow.user_id == user_id.value
        )
    )
    return frozenset(DeviceId.parse(value) for value in result.scalars().all())
