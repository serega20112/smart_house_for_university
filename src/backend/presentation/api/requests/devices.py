"""Request bodies for devices and translation to application commands."""

from __future__ import annotations

from pydantic import Field, field_validator

from backend.application.dto.devices.create_device_command import CreateDeviceCommand
from backend.application.dto.devices.update_device_command import UpdateDeviceCommand
from backend.domain.identifiers import EspDeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.presentation.api.base import StrictModel

NAME_MAX_LENGTH = 120
CHANNEL_MIN = 1
CHANNEL_MAX = 32


class DeviceCreateBody(StrictModel):
    """Describes a device the user wants to create.

    Kind and capabilities arrive as strings: the domain dictionary is the only place,
    where they mean something, and the request body only carries the text.

    Attributes:
        name: Name shown to the person.
        kind: What the device is for.
        channel: Relay channel the device is connected to.
        capabilities: Actions the device can perform.
        enabled: Whether the device can be controlled at all.
        automation_enabled: Whether the device participates in automation.
        board_id: Board the channel is on, or None for single-board home.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    kind: str
    channel: int = Field(ge=CHANNEL_MIN, le=CHANNEL_MAX)
    capabilities: list[str]
    enabled: bool = True
    automation_enabled: bool = True
    board_id: str | None = None

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str) -> str:
        """Rejects a kind unknown to the domain.

        Args:
            value: Named device kind.

        Returns:
            str: The same value if it can be parsed by the enumeration.
        """
        DeviceKind.parse(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def _known_capabilities(cls, value: list[str]) -> list[str]:
        """Rejects a capability absent from the domain dictionary.

        Args:
            value: Named capabilities.

        Returns:
            list[str]: The same values if each can be parsed by the enumeration.
        """
        for item in value:
            Capability.parse(item)
        return value


class DeviceUpdateBody(StrictModel):
    """Partial update of a device.

    Attributes:
        name: New name or None.
        kind: New kind or None.
        channel: New relay channel or None.
        capabilities: New capabilities or None.
        enabled: New enabled flag or None.
        automation_enabled: New automation enabled flag or None.
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
        """Rejects a kind unknown to the domain.

        Args:
            value: Named device kind or None to keep current.

        Returns:
            str | None: The same value if it can be parsed by the enumeration.
        """
        if value is not None:
            DeviceKind.parse(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def _known_capabilities(cls, value: list[str] | None) -> list[str] | None:
        """Rejects a capability absent from the domain dictionary.

        Args:
            value: Named capabilities or None to keep current.

        Returns:
            list[str] | None: The same values if each can be parsed by the enumeration.
        """
        if value is not None:
            for item in value:
                Capability.parse(item)
        return value


def create_command(body: DeviceCreateBody) -> CreateDeviceCommand:
    """Returns a create device command.

    Args:
        body: Describes the device to be created.

    Returns:
        CreateDeviceCommand: Command understandable by the application scenario.
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
    """Returns a update device command.

    Args:
        body: Fields to be changed.

    Returns:
        UpdateDeviceCommand: Command understandable by the application scenario.
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
