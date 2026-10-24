"""Ответы про логические устройства."""

from __future__ import annotations

from backend.application.dto.views.device_view import DeviceView
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
        board_id: Плата, на которой стоит канал, или None.
    """

    id: str
    name: str
    kind: str
    channel: int
    capabilities: list[str]
    enabled: bool
    automation_enabled: bool
    status: str
    board_id: str | None = None


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
        kind=device.kind.value,
        channel=device.channel,
        capabilities=sorted(item.value for item in device.capabilities),
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
        status=device.status.value,
        board_id=None if device.board_id is None else str(device.board_id),
    )
