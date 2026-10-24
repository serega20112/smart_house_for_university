"""Мапперы логического устройства и его способностей."""

from __future__ import annotations

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.relay_channel import RelayChannel
from backend.infrastructure.database.models import (
    DeviceCapabilityModel,
    DeviceModel,
)


def device_to_row(device: Device) -> DeviceModel:
    """Строит строку, описывающую логическое устройство."""
    return DeviceModel(
        id=device.id.value,
        user_id=device.user_id.value,
        name=device.name,
        kind=device.kind.value,
        channel=int(device.channel),
        board_id=None if device.board_id is None else device.board_id.value,
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
        version=device.version,
    )


def device_from_row(row: DeviceModel, capabilities: frozenset[Capability]) -> Device:
    """Строит устройство, описанное его строкой и строками способностей.

    Args:
        capabilities: Способности, прочитанные из ``device_capabilities``.
    """
    return Device(
        id=DeviceId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        name=row.name,
        kind=DeviceKind.parse(row.kind),
        channel=RelayChannel(row.channel),
        board_id=None if row.board_id is None else EspDeviceId.parse(row.board_id),
        capabilities=capabilities,
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
        version=row.version,
    )


def capability_rows(device: Device) -> list[DeviceCapabilityModel]:
    """Строит по строке на каждую способность логического устройства.

    Порядок задают явно, иначе множество давало бы разный файл на каждом запуске.
    """
    return [
        DeviceCapabilityModel(device_id=device.id.value, capability=capability.value)
        for capability in sorted(device.capabilities, key=lambda item: item.value)
    ]
