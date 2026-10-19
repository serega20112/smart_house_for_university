"""HTTP response schemas."""

from __future__ import annotations

import base64

from pydantic import BaseModel

from backend.application.dto import AuthenticatedUser, CommandResult
from backend.application.dto.device import DeviceExecutionResult
from backend.application.services import VoiceOutcome
from backend.application.use_cases.device import TurnAllResult
from backend.domain.entities.automation import AutomationSettings
from backend.domain.entities.device import Device
from backend.domain.entities.scenario import Scenario
from backend.domain.entities.user import (
    DashboardState,
    EspDevice,
    User,
    UserPreferences,
)
from backend.domain.enums.operation import OperationStatus
from backend.presentation.api import mappers
from backend.presentation.api.messages import (
    automation_toggled_message,
    command_message,
    execution_message,
    settings_saved_message,
    turn_all_message,
)


class DeviceResponse(BaseModel):
    """A device as returned by the API."""

    id: int
    name: str
    type: str
    physical_channel: int
    capabilities: list[str]
    enabled: bool
    automation_enabled: bool
    status: str

    @classmethod
    def from_device(cls, device: Device, status: str) -> DeviceResponse:
        """Build the response from a domain device.

        Args:
            device: Device to serialize.
            status: Current logical status of the device.

        Returns:
            DeviceResponse: API representation.
        """
        return cls(**mappers.device_payload(device, status))

    @classmethod
    def from_devices(cls, devices: list[Device], statuses: dict[int, str]) -> list[DeviceResponse]:
        """Build responses for a list of devices.

        Args:
            devices: Devices to serialize.
            statuses: Device identifiers mapped to their status.

        Returns:
            list[DeviceResponse]: API representations.
        """
        return [cls.from_device(device, statuses.get(device.id, "OFF")) for device in devices]


class AutomationResponse(BaseModel):
    """Automation settings as returned by the API."""

    enabled: bool
    target_temperature: float
    min_temperature: float
    max_temperature: float
    target_humidity: float
    min_humidity: float
    max_humidity: float
    participating_device_ids: list[int]

    @classmethod
    def from_settings(cls, settings: AutomationSettings) -> AutomationResponse:
        """Build the response from domain settings.

        Args:
            settings: Settings to serialize.

        Returns:
            AutomationResponse: API representation.
        """
        return cls(**mappers.automation_payload(settings))


class ScenarioResponse(BaseModel):
    """A scenario as returned by the API."""

    id: int
    status: str
    created_at: str
    start_at: str
    duration_minutes: int | None
    target: str | None
    actions: list[dict]
    completion_behavior: str

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> ScenarioResponse:
        """Build the response from a domain scenario.

        Args:
            scenario: Scenario to serialize.

        Returns:
            ScenarioResponse: API representation.
        """
        return cls(**mappers.scenario_payload(scenario))


class OperationResponse(BaseModel):
    """Generic result of a mutating request."""

    status: str
    message: str
    data: dict | None = None


class ExecutionResponse(BaseModel):
    """Result of a device command."""

    status: str
    message: str
    device: dict | None = None
    capability: str | None = None

    @classmethod
    def from_execution(cls, result: DeviceExecutionResult) -> ExecutionResponse:
        """Build the response from a device command result.

        Args:
            result: Result to serialize.

        Returns:
            ExecutionResponse: API representation.
        """
        payload = mappers.execution_payload(result)
        return cls(message=execution_message(result), **payload)

    @classmethod
    def from_turn_all(cls, result: TurnAllResult, on: bool) -> ExecutionResponse:
        """Build the response from a switch all result.

        Args:
            result: Result to serialize.
            on: Whether the devices were switched on.

        Returns:
            ExecutionResponse: API representation.
        """
        status = OperationStatus.SUCCESS if result.switched else OperationStatus.UNSUPPORTED
        return cls(status=status.value, message=turn_all_message(result, on))


class HomeStateResponse(BaseModel):
    """Full snapshot of the home state."""

    backend_online: bool
    esp_online: bool
    manual_override: bool
    temperature: float | None
    humidity: float | None
    devices: list[DeviceResponse]
    automation: AutomationResponse
    active_scenarios: list[ScenarioResponse]


class CommandResponse(BaseModel):
    """Answer to a free-form command."""

    status: str
    intent: str | None
    confidence: float
    message: str
    requires_clarification: bool
    clarification: str | None
    scenario_id: int | None

    @classmethod
    def from_result(cls, result: CommandResult) -> CommandResponse:
        """Build the response from a structured command result.

        Args:
            result: Result to serialize.

        Returns:
            CommandResponse: API representation.
        """
        return cls(
            status=result.status.value,
            intent=result.intent,
            confidence=result.confidence,
            message=command_message(result),
            requires_clarification=result.clarification is not None,
            clarification=None if result.clarification is None else result.clarification.value,
            scenario_id=result.scenario_id,
        )


class VoiceResponse(BaseModel):
    """Answer of a voice command.

    The same value is produced for a phrase spoken by the board, uploaded as
    audio or sent as text, so the interface and the tests see one shape.

    """

    status: str
    transcript: str
    intent: str | None = None
    message: str
    confidence: float = 0.0
    requires_clarification: bool = False
    clarification: str | None = None
    scenario_id: int | None = None
    audio_base64: str | None = None

    @classmethod
    def from_outcome(cls, outcome: VoiceOutcome) -> VoiceResponse:
        """Build the response from the outcome of a spoken phrase.

        Args:
            outcome: Result produced by the voice pipeline.

        Returns:
            VoiceResponse: API representation.
        """
        result = outcome.result
        audio = outcome.audio
        return cls(
            status=outcome.status,
            transcript=outcome.transcript,
            intent=outcome.intent,
            message=outcome.message,
            confidence=0.0 if result is None else result.confidence,
            requires_clarification=result is not None and result.clarification is not None,
            clarification=(
                None
                if result is None or result.clarification is None
                else result.clarification.value
            ),
            scenario_id=None if result is None else result.scenario_id,
            audio_base64=None if audio is None else base64.b64encode(audio).decode("ascii"),
        )


class SettingsResponse(BaseModel):
    """Answer of a settings update request."""

    status: str
    message: str
    automation: AutomationResponse


def settings_saved_response(settings: AutomationSettings) -> SettingsResponse:
    """Return the response of a settings update request.

    Args:
        settings: Stored settings.

    Returns:
        SettingsResponse: API representation.
    """
    return SettingsResponse(
        status=OperationStatus.SUCCESS.value,
        message=settings_saved_message(),
        automation=AutomationResponse.from_settings(settings),
    )


def automation_toggled_response(
    settings: AutomationSettings, enabled: bool
) -> SettingsResponse:
    """Return the response of a toggled automation mode.

    Args:
        settings: Stored settings.
        enabled: Desired state of the automation mode.

    Returns:
        SettingsResponse: API representation.
    """
    return SettingsResponse(
        status=OperationStatus.SUCCESS.value,
        message=automation_toggled_message(enabled),
        automation=AutomationResponse.from_settings(settings),
    )


class UserResponse(BaseModel):
    """A user profile as returned by the API."""

    id: str
    email: str
    display_name: str
    created_at: str

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        """Build the response from a domain account.

        Args:
            user: Account to serialize.

        Returns:
            UserResponse: API representation.
        """
        return cls(
            id=str(user.id),
            email=user.login,
            display_name=user.display_name,
            created_at=user.created_at.isoformat(),
        )


class SessionResponse(BaseModel):
    """An account together with the token proving who asked for it."""

    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserResponse

    @classmethod
    def from_session(cls, session: AuthenticatedUser) -> SessionResponse:
        """Build the response from an authorized session.

        Args:
            session: Authorized account with its token.

        Returns:
            SessionResponse: API representation.
        """
        return cls(
            access_token=session.token,
            expires_at=session.expires_at.isoformat(),
            user=UserResponse.from_user(session.user),
        )


class PreferencesResponse(BaseModel):
    """Interface preferences as returned by the API."""

    temperature_unit: str
    theme: str
    language: str
    show_command_chat: bool

    @classmethod
    def from_preferences(cls, preferences: UserPreferences) -> PreferencesResponse:
        """Build the response from domain preferences.

        Args:
            preferences: Preferences to serialize.

        Returns:
            PreferencesResponse: API representation.
        """
        return cls(
            temperature_unit=preferences.temperature_unit,
            theme=preferences.theme,
            language=preferences.language,
            show_command_chat=preferences.show_command_chat,
        )


class DashboardResponse(BaseModel):
    """Dashboard layout as returned by the API."""

    widgets: list[dict]

    @classmethod
    def from_dashboard(cls, dashboard: DashboardState) -> DashboardResponse:
        """Build the response from a domain layout.

        Args:
            dashboard: Layout to serialize.

        Returns:
            DashboardResponse: API representation.
        """
        return cls(widgets=dashboard.to_dict()["widgets"])


class EspDeviceResponse(BaseModel):
    """A paired board as returned by the API."""

    id: int
    name: str
    online: bool
    last_seen_at: str | None
    pairing_key: str | None = None

    @classmethod
    def from_board(
        cls, board: EspDevice, online: bool, reveal_key: bool = False
    ) -> EspDeviceResponse:
        """Build the response from a paired board.

        The pairing key is a credential, so it is only revealed in the answer to
        the request that created the board.

        Args:
            board: Board to serialize.
            online: Whether a board of the owner is connected right now.
            reveal_key: Whether the pairing key is included.

        Returns:
            EspDeviceResponse: API representation.
        """
        return cls(
            id=board.id,
            name=board.name,
            online=online,
            last_seen_at=None if board.last_seen_at is None else board.last_seen_at.isoformat(),
            pairing_key=board.pairing_key if reveal_key else None,
        )


class ClaimResponse(BaseModel):
    """A board an account just took over.

    The pairing key of a taken board is never revealed: nobody has to type it
    anywhere, so the only place it exists is the flash of the board itself.

    """

    id: int
    name: str

    @classmethod
    def from_device(cls, board: EspDevice) -> ClaimResponse:
        """Build the response from a paired board.

        Args:
            board: Board that was taken.

        Returns:
            ClaimResponse: API representation.
        """
        return cls(id=board.id, name=board.name)


def error_detail(message: str) -> str:
    """Return a detail payload for an HTTP error.

    Args:
        message: Human readable reason.

    Returns:
        str: Detail of the error.
    """
    return message