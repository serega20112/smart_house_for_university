"""Общие тестовые данные для устройств: владелец и фабрика устройств."""

from __future__ import annotations

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.relay_channel import RelayChannel

OWNER_UUID = "11111111-1111-1111-1111-111111111111"


def make_device(
    *,
    name: str = "Test device",
    user_id: UserId | None = None,
    kind: DeviceKind = DeviceKind.LIGHT,
    channel: RelayChannel | int = RelayChannel(1),
    board_id: EspDeviceId | None = None,
    capabilities: frozenset[Capability] | None = None,
    enabled: bool = True,
    automation_enabled: bool = True,
) -> Device:
    """Построить тестовое устройство с разумными значениями по умолчанию.

    Args:
        name: Имя устройства.
        user_id: Владелец, по умолчанию общий владелец тестов.
        kind: Назначение устройства.
        channel: Канал реле (int или RelayChannel).
        board_id: Плата или None для дома без привязки к плате.
        capabilities: Способности, по умолчанию ON и OFF.
        enabled: Разрешено ли управление.
        automation_enabled: Участвует ли в автоматизации.

    Returns:
        Device: Собранное устройство.
    """
    if user_id is None:
        user_id = UserId.parse(OWNER_UUID)
    if isinstance(channel, int):
        channel = RelayChannel(channel)
    if capabilities is None:
        capabilities = frozenset({Capability.ON, Capability.OFF})
    return Device.create(
        user_id=user_id,
        name=name,
        kind=kind,
        channel=channel,
        board_id=board_id,
        capabilities=capabilities,
        enabled=enabled,
        automation_enabled=automation_enabled,
    )
