"""HTTP request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from smart_home_backend.application.dto import (
    CreateDeviceCommand,
    UpdateAutomationCommand,
    UpdateDeviceCommand,
)
from smart_home_backend.domain.enums.device import RELAY_CHANNEL_COUNT


class DeviceCreateBody(BaseModel):
    """Body of a device creation request."""

    name: str
    type: str = "OTHER"
    physical_channel: int = Field(ge=1, le=RELAY_CHANNEL_COUNT)
    capabilities: list[str] = Field(default_factory=lambda: ["ON", "OFF"])
    enabled: bool = True
    automation_enabled: bool = True

    def to_command(self) -> CreateDeviceCommand:
        """Return the application command described by the body.

        Returns:
            CreateDeviceCommand: Command for the use case.
        """
        return CreateDeviceCommand(
            name=self.name,
            type=self.type,
            physical_channel=self.physical_channel,
            capabilities=self.capabilities,
            enabled=self.enabled,
            automation_enabled=self.automation_enabled,
        )


class DeviceUpdateBody(BaseModel):
    """Body of a device update request."""

    name: str | None = None
    type: str | None = None
    physical_channel: int | None = Field(default=None, ge=1, le=RELAY_CHANNEL_COUNT)
    capabilities: list[str] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None

    def to_command(self) -> UpdateDeviceCommand:
        """Return the application command described by the body.

        Returns:
            UpdateDeviceCommand: Command for the use case.
        """
        return UpdateDeviceCommand(
            name=self.name,
            type=self.type,
            physical_channel=self.physical_channel,
            capabilities=self.capabilities,
            enabled=self.enabled,
            automation_enabled=self.automation_enabled,
        )


class DeviceModeBody(BaseModel):
    """Body of a device mode request."""

    mode: str


class AutomationUpdateBody(BaseModel):
    """Body of an automation settings update request."""

    enabled: bool | None = None
    target_temperature: float | None = None
    temperature_tolerance: float | None = None
    target_humidity: float | None = None
    humidity_tolerance: float | None = None
    participating_device_ids: list[int] | None = None

    def to_command(self) -> UpdateAutomationCommand:
        """Return the application command described by the body.

        Returns:
            UpdateAutomationCommand: Command for the use case.
        """
        return UpdateAutomationCommand(
            enabled=self.enabled,
            target_temperature=self.target_temperature,
            temperature_tolerance=self.temperature_tolerance,
            target_humidity=self.target_humidity,
            humidity_tolerance=self.humidity_tolerance,
            participating_device_ids=self.participating_device_ids,
        )


class ScenarioCreateBody(BaseModel):
    """Body of a scenario creation request."""

    delay_minutes: int | None = Field(default=None, ge=0)
    target_temperature: float | None = None
    capability: str | None = None
    completion_behavior: str = "CONTINUE_AUTOMATION"
    target: str | None = None


class CommandBody(BaseModel):
    """Body of a free-form command request."""

    text: str
