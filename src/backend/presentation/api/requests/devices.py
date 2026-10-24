"""Тела запросов устройств и перевод их в команды приложения."""

from __future__ import annotations

from pydantic import Field, field_validator

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

    Назначение и способности приходят строками: словарь домена — единственное место,
    где они значат что-то, а тело запроса только переносит текст.

    Attributes:
        name: Имя, показанное человеку.
        kind: Назначение устройства.
        channel: Канал реле, к которому устройство подключают.
        capabilities: Действия, которые устройство умеет.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    kind: str
    channel: int = Field(ge=CHANNEL_MIN, le=CHANNEL_MAX)
    capabilities: list[str]
    enabled: bool = True
    automation_enabled: bool = True

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str) -> str:
        """Отвергает назначение, которого домен не знает.

        Args:
            value: Названное назначение устройства.

        Returns:
            str: То же значение, если оно читается перечислением.
        """
        DeviceKind.parse(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def _known_capabilities(cls, value: list[str]) -> list[str]:
        """Отвергает способность, которой нет в словаре домена.

        Args:
            value: Названные способности.

        Returns:
            list[str]: Те же значения, если каждое читается перечислением.
        """
        for item in value:
            Capability.parse(item)
        return value


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
    kind: str | None = None
    channel: int | None = Field(default=None, ge=CHANNEL_MIN, le=CHANNEL_MAX)
    capabilities: list[str] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str | None) -> str | None:
        """Отвергает назначение, которого домен не знает.

        Args:
            value: Названное назначение или None оставить нынешнее.

        Returns:
            str | None: То же значение, если оно читается перечислением.
        """
        if value is not None:
            DeviceKind.parse(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def _known_capabilities(cls, value: list[str] | None) -> list[str] | None:
        """Отвергает способность, которой нет в словаре домена.

        Args:
            value: Названные способности или None оставить нынешние.

        Returns:
            list[str] | None: Те же значения, если каждое читается перечислением.
        """
        if value is not None:
            for item in value:
                Capability.parse(item)
        return value


def create_command(body: DeviceCreateBody) -> CreateDeviceCommand:
    """Возвращает команду создания устройства.

    Args:
        body: Описывает заводимое устройство.

    Returns:
        CreateDeviceCommand: Команда, понятная сценарию приложения.
    """
    return CreateDeviceCommand(
        name=body.name,
        kind=DeviceKind.parse(body.kind),
        channel=body.channel,
        capabilities=frozenset(Capability.parse(item) for item in body.capabilities),
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
        kind=None if body.kind is None else DeviceKind.parse(body.kind),
        channel=body.channel,
        capabilities=(
            None
            if body.capabilities is None
            else frozenset(Capability.parse(item) for item in body.capabilities)
        ),
        enabled=body.enabled,
        automation_enabled=body.automation_enabled,
    )
