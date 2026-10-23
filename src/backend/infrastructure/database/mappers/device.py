"""Мапперы логического устройства и его способностей."""

from __future__ import annotations

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.relay_channel import RelayChannel
from backend.infrastructure.database.tables import (
    DeviceCapabilityRow,
    DeviceRow,
)


def device_to_row(device: Device) -> DeviceRow:
    """Build the row describing a logical device.

    Args:
        device: Device to serialize.

    Returns:
        DeviceRow: New row describing the device.
    """
    return DeviceRow(
        id=device.id.value,
        user_id=device.user_id.value,
        name=device.name,
        kind=device.kind.value,
        channel=int(device.channel),
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
        version=device.version,
    )


def device_from_row(row: DeviceRow, capabilities: frozenset[Capability]) -> Device:
    """Build the device a row and its capability rows describe.

    Args:
        row: Row to deserialize.
        capabilities: Capabilities read from ``device_capabilities``.

    Returns:
        Device: Restored device.
    """
    return Device(
        id=DeviceId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        name=row.name,
        kind=DeviceKind.parse(row.kind),
        channel=RelayChannel(row.channel),
        capabilities=capabilities,
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
        version=row.version,
    )


def capability_rows(device: Device) -> list[DeviceCapabilityRow]:
    """Build one row per capability of a logical device.

    Args:
        device: Device to serialize.

    Returns:
        list[DeviceCapabilityRow]: Capability rows of the device.
    """
    return [
        DeviceCapabilityRow(device_id=device.id.value, capability=capability.value)
        for capability in sorted(device.capabilities, key=lambda item: item.value)
    ]
