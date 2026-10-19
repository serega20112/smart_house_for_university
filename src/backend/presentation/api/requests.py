"""HTTP request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.application.dto import (
    AuthenticateUserCommand,
    CreateDeviceCommand,
    RegisterUserCommand,
    UpdateAutomationCommand,
    UpdateDashboardCommand,
    UpdateDeviceCommand,
    UpdatePreferencesCommand,
)
from backend.domain.entities.user import DashboardWidget
from backend.domain.enums.device import RELAY_CHANNEL_COUNT


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


class VoiceTextBody(BaseModel):
    """Body of a voice command request addressed by text.

    Useful for debugging the neural understanding of a phrase without any audio
    involved: the transcription step is the only one being skipped.

    """

    text: str = Field(min_length=1, max_length=500)


class RegisterBody(BaseModel):
    """Body of a registration request."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    display_name: str = Field(min_length=1, max_length=80)

    def to_command(self) -> RegisterUserCommand:
        """Return the application command described by the body.

        Returns:
            RegisterUserCommand: Command for the use case.
        """
        return RegisterUserCommand(
            email=self.email, password=self.password, display_name=self.display_name
        )


class LoginBody(BaseModel):
    """Body of an authorization request."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

    def to_command(self) -> AuthenticateUserCommand:
        """Return the application command described by the body.

        Returns:
            AuthenticateUserCommand: Command for the use case.
        """
        return AuthenticateUserCommand(email=self.email, password=self.password)


class PreferencesUpdateBody(BaseModel):
    """Body of a preferences update request."""

    temperature_unit: str | None = None
    theme: str | None = None
    language: str | None = None
    show_command_chat: bool | None = None

    def to_command(self) -> UpdatePreferencesCommand:
        """Return the application command described by the body.

        Returns:
            UpdatePreferencesCommand: Command for the use case.
        """
        return UpdatePreferencesCommand(
            temperature_unit=self.temperature_unit,
            theme=self.theme,
            language=self.language,
            show_command_chat=self.show_command_chat,
        )


class WidgetBody(BaseModel):
    """One entry of a dashboard layout request."""

    type: str
    device_id: int | None = None
    title: str | None = Field(default=None, max_length=60)


class DashboardUpdateBody(BaseModel):
    """Body of a dashboard layout update request."""

    widgets: list[WidgetBody] = Field(default_factory=list, max_length=40)

    def to_command(self) -> UpdateDashboardCommand:
        """Return the application command described by the body.

        Returns:
            UpdateDashboardCommand: Command for the use case.
        """
        return UpdateDashboardCommand(
            widgets=[
                DashboardWidget(type=item.type, device_id=item.device_id, title=item.title)
                for item in self.widgets
            ]
        )


class PairEspDeviceBody(BaseModel):
    """Body of a board pairing request."""

    name: str = Field(min_length=1, max_length=60)
    pairing_key: str | None = Field(default=None, max_length=64)


class ClaimEspDeviceBody(BaseModel):
    """Body of a board takeover request.

    The token comes from the offer the board published when it asked to be taken,
    so nothing about the board has to be copied by hand.
    """

    claim_token: str = Field(min_length=6, max_length=16)
    name: str = Field(min_length=1, max_length=60)