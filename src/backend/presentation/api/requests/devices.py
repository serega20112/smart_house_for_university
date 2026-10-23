"""Тела запросов устройств и перевод их в команды приложения."""

from __future__ import annotations

from pydantic import Field

from backend.application.dto.devices.create_device_command import CreateDeviceCommand
from backend.application.dto.devices.update_device_command import UpdateDeviceCommand
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.presentation.api.base import StrictModel

NAME_MAX_LENGTH = 120
CHANNEL_MIN = 1
CHANNEL_MAX = 32


class DeviceCreateBody(StrictModel):
    """Описывает устройство, которое человек хочет завести.

    Attributes:
        name: Имя, показанное человеку.
        kind: Назначение устройства.
        channel: Канал реле, к которому устройство подключают.
        capabilities: Действия, которые устройство умеет.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    kind: DeviceKind
    channel: int = Field(ge=CHANNEL_MIN, le=CHANNEL_MAX)
    capabilities: list[Capability]
    enabled: bool = True
    automation_enabled: bool = True


class DeviceUpdateBody(StrictModel):
    """Частичное изменение устройства.

    Attributes:
        name: Новое имя или None.
        kind: Новое назначение или None.
        channel: Новый канал реле или None.
        capabilities: Новые способности или None.
        enabled: Новый признак доступности или None.
        automation_enabled: Новый признак автоматизации или None.
    """

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    kind: DeviceKind | None = None
    channel: int | None = Field(default=None, ge=CHANNEL_MIN, le=CHANNEL_MAX)
    capabilities: list[Capability] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None


def create_command(body: DeviceCreateBody) -> CreateDeviceCommand:
    """Возвращает команду создания устройства.

    Args:
        body: Описывает заводимое устройство.

    Returns:
        CreateDeviceCommand: Команда, понятная сценарию приложения.
    """
    return CreateDeviceCommand(
        name=body.name,
        kind=body.kind,
        channel=body.channel,
        capabilities=frozenset(body.capabilities),
        enabled=body.enabled,
        automation_enabled=body.automation_enabled,
    )


def update_command(body: DeviceUpdateBody) -> UpdateDeviceCommand:
    """Возвращает команду частичного изменения устройства.

    Args:
        body: Поля, которые нужно изменить.

    Returns:
        UpdateDeviceCommand: Команда, понятная сценарию приложения.
    """
    return UpdateDeviceCommand(
        name=body.name,
        kind=body.kind,
        channel=body.channel,
        capabilities=None if body.capabilities is None else frozenset(body.capabilities),
        enabled=body.enabled,
        automation_enabled=body.automation_enabled,
    )
