"""Bodies of the requests and the responses of the HTTP API.

Pydantic models live in the presentation layer and nowhere else: the application
layer speaks in frozen dataclasses, and the two shapes are converted into each
other by the mappers of this package.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from smart_home.application.dto import (
    AccountProfile,
    AuthenticatedSession,
    AutomationView,
    BoardClaimView,
    BoardNetworkView,
    BoardView,
    Capability,
    CompletionBehavior,
    DeviceKind,
    DeviceStatus,
    DeviceView,
    ScenarioView,
)


class StrictModel(BaseModel):
    """Common behaviour of every body of the API.

    Attributes:
        None.

    """

    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    """Availability of the service.

    Attributes:
        status: Availability of the service.
        name: Name of the deployment.
        version: Version of the running build.

    """

    status: str
    name: str
    version: str


class UserResponse(StrictModel):
    """Account as the interface sees it.

    Attributes:
        id: Identifier of the account.
        email: Login of the account.
        display_name: Name shown in the interface.
        created_at: Moment the account was created.

    """

    id: str
    email: str
    display_name: str
    created_at: datetime


class SessionResponse(StrictModel):
    """Session handed out to a client.

    Attributes:
        access_token: Token sent with every following request.
        token_type: Scheme the token is sent with.
        expires_at: Moment the token stops being accepted.
        user: Profile of the signed in account.

    """

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


class RegisterBody(StrictModel):
    """Registration request.

    Attributes:
        email: Login the person chose.
        display_name: Name they want to be called by.
        password: Plain password.

    """

    email: str
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)


class LoginBody(StrictModel):
    """Login request.

    Attributes:
        email: Login of the account.
        password: Plain password.

    """

    email: str
    password: str


class DeviceResponse(StrictModel):
    """One device as the interface sees it.

    Attributes:
        id: Identifier of the device.
        name: Name shown to the user.
        kind: What the device is for.
        channel: Relay channel the device is wired to.
        capabilities: Actions the device is able to perform.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device takes part in automation.
        status: What the device is doing right now.

    """

    id: str
    name: str
    kind: DeviceKind
    channel: int
    capabilities: list[Capability]
    enabled: bool
    automation_enabled: bool
    status: DeviceStatus


class DeviceCreateBody(StrictModel):
    """Description of a device the user wants to add.

    Attributes:
        name: Name shown to the user.
        kind: What the device is for.
        channel: Relay channel the device is wired to.
        capabilities: Actions the device is able to perform.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device takes part in automation.

    """

    name: str = Field(min_length=1, max_length=120)
    kind: DeviceKind
    channel: int = Field(ge=1, le=32)
    capabilities: list[Capability]
    enabled: bool = True
    automation_enabled: bool = True


class DeviceUpdateBody(StrictModel):
    """Partial change of a device.

    Attributes:
        name: New name or None.
        kind: New kind or None.
        channel: New relay channel or None.
        capabilities: New capabilities or None.
        enabled: New availability flag or None.
        automation_enabled: New automation flag or None.

    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: DeviceKind | None = None
    channel: int | None = Field(default=None, ge=1, le=32)
    capabilities: list[Capability] | None = None
    enabled: bool | None = None
    automation_enabled: bool | None = None


class ScenarioResponse(StrictModel):
    """One scenario as the interface sees it.

    Attributes:
        id: Identifier of the scenario.
        status: Stage the scenario is in.
        created_at: Moment the scenario was stored.
        start_at: Moment the scenario starts acting.
        duration_minutes: How long it may run, or None when it is unbounded.
        target: Area or object the user named.
        completion_behavior: What happens with the devices afterwards.
        actions: Actions the scenario performs.

    """

    id: str
    status: str
    created_at: datetime
    start_at: datetime
    duration_minutes: int | None
    target: str | None
    completion_behavior: CompletionBehavior
    actions: list[ScenarioActionResponse]


class ScenarioActionResponse(StrictModel):
    """One action of a scenario.

    Attributes:
        capability: Capability the action performs.
        target_temperature: Temperature the action aims for, or None.

    """

    capability: Capability
    target_temperature: float | None


class ScenarioCreateBody(StrictModel):
    """Request to schedule a scenario.

    Attributes:
        capability: Capability the scenario performs.
        delay_minutes: How long to wait before acting.
        target: Area or object the user named.
        target_temperature: Temperature the scenario aims for, or None.
        completion_behavior: What happens with the devices afterwards.
        duration_minutes: How long the scenario may run.

    """

    capability: Capability
    delay_minutes: int | None = Field(default=None, ge=0, le=10080)
    target: str | None = None
    target_temperature: float | None = Field(default=None, ge=-50.0, le=80.0)
    completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)


class AutomationResponse(StrictModel):
    """Automation configuration as the interface sees it.

    Attributes:
        enabled: Whether automation is active.
        target_temperature: Temperature the home is asked to hold.
        temperature_tolerance: How far the temperature may drift.
        target_humidity: Humidity the home is asked to hold.
        humidity_tolerance: How far the humidity may drift.
        participating_device_ids: Devices automation is allowed to drive.

    """

    enabled: bool
    target_temperature: float
    target_humidity: float
    temperature_tolerance: float
    humidity_tolerance: float
    participating_device_ids: list[str]


class AutomationUpdateBody(StrictModel):
    """Partial change of the automation configuration.

    Attributes:
        enabled: New automation flag or None.
        target_temperature: New target temperature or None.
        temperature_tolerance: New temperature tolerance or None.
        target_humidity: New target humidity or None.
        humidity_tolerance: New humidity tolerance or None.
        participating_device_ids: New participants or None.

    """

    enabled: bool | None = None
    target_temperature: float | None = Field(default=None, ge=-50.0, le=80.0)
    temperature_tolerance: float | None = Field(default=None, ge=0.0, le=20.0)
    target_humidity: float | None = Field(default=None, ge=0.0, le=100.0)
    humidity_tolerance: float | None = Field(default=None, ge=0.0, le=50.0)
    participating_device_ids: list[str] | None = None


class ReadingResponse(StrictModel):
    """Climate values as the interface sees them.

    Attributes:
        temperature: Measured temperature or None.
        humidity: Measured relative humidity or None.

    """

    temperature: float | None
    humidity: float | None


class HomeStateResponse(StrictModel):
    """Everything one screen of the interface has to render.

    Attributes:
        board_online: Whether any board of the account is connected.
        automation_suspended: Whether manual control is holding automation back.
        reading: Climate values right now.
        devices: Devices with their current status.
        automation: Automation configuration.
        active_scenarios: Scenarios that still outrank automation.

    """

    board_online: bool
    automation_suspended: bool
    reading: ReadingResponse
    devices: list[DeviceResponse]
    automation: AutomationResponse
    active_scenarios: list[ScenarioResponse]


class BoardResponse(StrictModel):
    """One board as the interface sees it.

    Attributes:
        id: Identifier of the board.
        name: Name shown to the user.
        online: Whether the board is connected right now.
        last_seen_at: Moment of the last successful handshake, or None.
        current_ssid: Network the board reported being on, or None.

    """

    id: str
    name: str
    online: bool
    last_seen_at: datetime | None
    current_ssid: str | None


class BoardClaimResponse(StrictModel):
    """One offer of a board waiting for an owner.

    Attributes:
        id: Identifier of the offer.
        label: Short code shown next to the board.
        claim_token: Token the user has to send to take the board.
        announced_at: Moment the board announced itself.
        expires_at: Moment the offer stops being valid.

    """

    id: str
    label: str
    claim_token: str
    announced_at: datetime
    expires_at: datetime


class ClaimBoardBody(StrictModel):
    """Request to take an announced board.

    Attributes:
        claim_token: Token of the offer.
        name: Name the user wants the board to have.

    """

    claim_token: str
    name: str = Field(min_length=1, max_length=120)


class PairBoardBody(StrictModel):
    """Request to pair a board from the interface.

    Attributes:
        name: Name shown to the user.
        pairing_key: Key chosen by the user, or None to let the system generate one.

    """

    name: str = Field(min_length=1, max_length=120)
    pairing_key: str | None = None


class BoardNetworkBody(StrictModel):
    """Network a board is told to use.

    Attributes:
        ssid: Name of the wireless network.
        password: Password of that network, empty when the network is open.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.

    """

    ssid: str = Field(min_length=1, max_length=64)
    password: str = Field(max_length=128)
    host: str = Field(min_length=1, max_length=255)
    server_port: int = Field(ge=1, le=65535)
    socket_port: int = Field(ge=1, le=65535)
    socket_path: str = Field(min_length=1, max_length=255)


class BoardNetworkResponse(StrictModel):
    """Network of a board as the interface sees it.

    Attributes:
        board_id: Identifier of the board.
        ssid: Name of the wireless network the board is told to use.
        host: Address of the server the board is told to report to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.
        configured: Whether the board already has a network of its own.
        updated_at: Moment the settings were written, or None.

    """

    board_id: str
    ssid: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
    configured: bool
    updated_at: datetime | None


class CommandBody(StrictModel):
    """Free form sentence submitted by a person.

    Attributes:
        text: The sentence as typed or as transcribed.

    """

    text: str = Field(min_length=1, max_length=2000)


class CommandResponse(StrictModel):
    """What carrying a command out produced.

    Attributes:
        intent: Intent that was carried out, or None.
        answer: Text describing what happened.
        message: The same text under the name older clients read.
        details: Machine readable extras.

    """

    intent: str | None
    answer: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class VoiceTextBody(StrictModel):
    """A sentence submitted to the voice pipeline as text.

    Attributes:
        text: The sentence as typed.

    """

    text: str = Field(min_length=1, max_length=500)


class VoiceResponse(StrictModel):
    """Answer of the voice pipeline.

    Attributes:
        status: Name of the outcome.
        transcript: Text that was recognized, empty when a command was typed.
        answer: Phrase produced for the person.
        audio_base64: Rendered answer encoded for the browser, or None.

    """

    status: str
    transcript: str
    answer: str
    audio_base64: str | None = None


class VoiceStatusResponse(StrictModel):
    """Availability and configuration of the voice pipeline.

    Attributes:
        active: Whether speech recognition is available.
        sample_rate: Sample rate the boards are told to use.
        max_audio_sec: Longest phrase a board may send.
        board_online: Whether a board of the account is connected.
        message: Text shown to the person.

    """

    active: bool
    sample_rate: int
    max_audio_sec: int
    board_online: bool
    message: str


class BoardPairedResponse(StrictModel):
    """A board that was just paired, with its key revealed exactly once.

    Attributes:
        id: Identifier of the board.
        name: Name shown to the user.
        pairing_key: Secret the board has to present while dialing in.

    """

    id: str
    name: str
    pairing_key: str


class OperationResponse(StrictModel):
    """Result of an operation that changed nothing but a flag.

    Attributes:
        status: Name of the outcome.
        message: Text shown to the person.

    """

    status: str
    message: str


def session_of(session: AuthenticatedSession) -> SessionResponse:
    """Return the body of a session.

    Args:
        session: Session the application issued.

    Returns:
        SessionResponse: Body of the session.
    """
    return SessionResponse(
        access_token=session.token,
        expires_at=session.expires_at,
        user=profile_of(session.profile),
    )


def profile_of(profile: AccountProfile) -> UserResponse:
    """Return the body of an account profile.

    Args:
        profile: Profile of the account.

    Returns:
        UserResponse: Body of the profile.
    """
    return UserResponse(
        id=str(profile.id),
        email=profile.email,
        display_name=profile.display_name,
        created_at=profile.created_at,
    )


def device_of(device: DeviceView) -> DeviceResponse:
    """Return the body of a device.

    Args:
        device: Device as the application sees it.

    Returns:
        DeviceResponse: Body of the device.
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


def scenario_of(scenario: ScenarioView) -> ScenarioResponse:
    """Return the body of a scenario.

    Args:
        scenario: Scenario as the application sees it.

    Returns:
        ScenarioResponse: Body of the scenario.
    """
    return ScenarioResponse(
        id=str(scenario.id),
        status=scenario.status.value,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior,
        actions=[
            ScenarioActionResponse(
                capability=action.capability,
                target_temperature=(
                    None if action.target_temperature is None else action.target_temperature.celsius
                ),
            )
            for action in scenario.actions
        ],
    )


def automation_of(automation: AutomationView) -> AutomationResponse:
    """Return the body of the automation configuration.

    Args:
        automation: Configuration as the application sees it.

    Returns:
        AutomationResponse: Body of the configuration.
    """
    return AutomationResponse(
        enabled=automation.enabled,
        target_temperature=automation.target_temperature,
        target_humidity=automation.target_humidity,
        temperature_tolerance=automation.temperature_tolerance,
        humidity_tolerance=automation.humidity_tolerance,
        participating_device_ids=sorted(str(item) for item in automation.participating_device_ids),
    )


def board_of(board: BoardView) -> BoardResponse:
    """Return the body of a board.

    Args:
        board: Board as the application sees it.

    Returns:
        BoardResponse: Body of the board.
    """
    return BoardResponse(
        id=str(board.id),
        name=board.name,
        online=board.online,
        last_seen_at=board.last_seen_at,
        current_ssid=board.current_ssid,
    )


def claim_of(claim: BoardClaimView) -> BoardClaimResponse:
    """Return the body of an offer of a board.

    Args:
        claim: Offer as the application sees it.

    Returns:
        BoardClaimResponse: Body of the offer.
    """
    return BoardClaimResponse(
        id=str(claim.id),
        label=claim.label,
        claim_token=claim.claim_token,
        announced_at=claim.announced_at,
        expires_at=claim.expires_at,
    )


def network_of(network: BoardNetworkView) -> BoardNetworkResponse:
    """Return the body of the network of a board.

    Args:
        network: Network as the application sees it.

    Returns:
        BoardNetworkResponse: Body of the network.
    """
    return BoardNetworkResponse(
        board_id=str(network.board_id),
        ssid=network.ssid,
        host=network.host,
        server_port=network.server_port,
        socket_port=network.socket_port,
        socket_path=network.socket_path,
        configured=network.configured,
        updated_at=network.updated_at,
    )
