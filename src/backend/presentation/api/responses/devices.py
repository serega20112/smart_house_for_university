"""Ответы про логические устройства."""

from __future__ import annotations

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.presentation.api.responses.common import StrictModel


class DeviceResponse(StrictModel):
    """Одно устройство таким, каким его видит интерфейс.

    Attributes:
        id: Идентификатор устройства.
        name: Имя, показанное человеку.
        kind: Назначение устройства.
        channel: Канал реле, к которому устройство подключено.
        capabilities: Действия, которые устройство умеет.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
        status: Что устройство делает сейчас.
    """

    id: str
    name: str
    kind: DeviceKind
    channel: int
    capabilities: list[Capability]
    enabled: bool
    automation_enabled: bool
    status: DeviceStatus


def device_of(device: DeviceView) -> DeviceResponse:
    """Возвращает тело устройства.

    Args:
        device: Устройство таким, каким его видит прикладной слой.

    Returns:
        DeviceResponse: Тело устройства.
    """
    return DeviceResponse(
        id=str(device.id),
        name=device.name,
        kind=device.kind,
        channel=device.channel,
        capabilities=sorted(device.capabilities, key=str),
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
        status=device.status,
    )
