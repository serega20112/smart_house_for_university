"""Тела запросов устройств и перевод их в команды приложения."""

from __future__ import annotations

from pydantic import Field, field_validator

from backend.application.dto.devices.create_device_command import CreateDeviceCommand
from backend.application.dto.devices.update_device_command import UpdateDeviceCommand
from backend.domain.identifiers import EspDeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_name import DeviceName
from backend.domain.value_objects.devices.relay_channel import FIRST_CHANNEL, RELAY_COUNT
from backend.presentation.api.base import StrictModel
from backend.presentation.api.requests.validation import known_to_domain


class DeviceCreateBody(StrictModel):
    """Описывает устройство, которое человек хочет создать.

    Тип и способности приходят текстом: словарь домена — единственное место, где они
    что-то означают, а тело запроса несёт только текст.

    Attributes:
        name: Имя, показанное человеку.
        kind: Для чего устройство.
        channel: Канал реле, к которому подключено устройство.
        capabilities: Действия, которые устройство умеет выполнять.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
        board_id: Плата, на которой стоит канал, или None для дома с одной платой.
    """

    name: str = Field(min_length=1, max_length=DeviceName.MAX_LENGTH)
    kind: str
    channel: int = Field(ge=FIRST_CHANNEL, le=RELAY_COUNT)
    capabilities: list[str]
    enabled: bool = True
    automation_enabled: bool = True
    board_id: str | None = None

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str) -> str:
        """Отвергает тип, которого нет в словаре домена.

        Args:
            value: Названный тип устройства.

        Returns:
            str: То же значение, если оно читается перечислением.
        """
        return known_to_domain(DeviceKind.parse, value)

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
            known_to_domain(Capability.parse, item)
        return value


class DeviceUpdateBody(StrictModel):
    """Частичное изменение устройства.

    Attributes:
        name: Новое имя или None, чтобы оставить текущее.
        kind: Новый тип или None, чтобы оставить текущий.
        channel: Новый канал реле или None, чтобы оставить текущий.
        board_id: Новая плата или None, чтобы оставить текущую.
        capabilities: Новые способности или None, чтобы оставить текущие.
        enabled: Новый признак управления или None, чтобы оставить текущий.
        automation_enabled: Новый признак участия в автоматизации или None.
    """

    name: str | None = Field(default=None, min_length=1, max_length=DeviceName.MAX_LENGTH)
    kind: str | None = None
    channel: int | None = Field(default=None, ge=FIRST_CHANNEL, le=RELAY_COUNT)
    board_id: str | None = None
    capabilities: list[str] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str | None) -> str | None:
        """Отвергает тип, которого нет в словаре домена.

        Args:
            value: Названный тип устройства или None, чтобы оставить текущий.

        Returns:
            str | None: То же значение, если оно читается перечислением.
        """
        if value is not None:
            known_to_domain(DeviceKind.parse, value)
        return value

    @field_validator("capabilities")
    @classmethod
    def _known_capabilities(cls, value: list[str] | None) -> list[str] | None:
        """Отвергает способность, которой нет в словаре домена.

        Args:
            value: Названные способности или None, чтобы оставить текущие.

        Returns:
            list[str] | None: Те же значения, если каждое читается перечислением.
        """
        if value is not None:
            for item in value:
                known_to_domain(Capability.parse, item)
        return value


def create_command(body: DeviceCreateBody) -> CreateDeviceCommand:
    """Возвращает команду создания устройства.

    Args:
        body: Описание устройства, которое нужно создать.

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
        board_id=None if body.board_id is None else EspDeviceId.parse(body.board_id),
    )


def update_command(body: DeviceUpdateBody) -> UpdateDeviceCommand:
    """Возвращает команду изменения устройства.

    Args:
        body: Поля, которые нужно изменить.

    Returns:
        UpdateDeviceCommand: Команда, понятная сценарию приложения.
    """
    return UpdateDeviceCommand(
        name=body.name,
        kind=None if body.kind is None else DeviceKind.parse(body.kind),
        channel=body.channel,
        board_id=None if body.board_id is None else EspDeviceId.parse(body.board_id),
        capabilities=(
            None
            if body.capabilities is None
            else frozenset(Capability.parse(item) for item in body.capabilities)
        ),
        enabled=body.enabled,
        automation_enabled=body.automation_enabled,
    )
