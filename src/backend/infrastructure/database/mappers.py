"""Translation between domain aggregates and table rows.

Every conversion in this module is a pure function: it takes an aggregate or a
row and returns a value of the other kind, and it never touches a session. That
is what makes the translation testable on its own and keeps the identity rules of
the model in one readable place.

Nothing here writes to an aggregate. Entities are built through their own public
constructors, so no infrastructure code ever assigns to a private field of a
domain object, and an identifier is always taken from the aggregate rather than
handed out by the store.

Enumerations are translated to and from their textual value here and nowhere
else, because that is the single place allowed to know how an enumeration is
written down.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Table

from backend.domain.accounts.display_name import DisplayName
from backend.domain.accounts.email import Email
from backend.domain.accounts.user import User
from backend.domain.boards.board_network import BoardNetwork
from backend.domain.boards.esp_claim import EspClaim
from backend.domain.boards.esp_device import EspDevice
from backend.domain.boards.network_profile import NetworkProfile
from backend.domain.boards.pairing_key import PairingKey
from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.climate.humidity import Humidity
from backend.domain.climate.temperature import Temperature
from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.devices.device_kind import DeviceKind
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.devices.relay_channel import RelayChannel
from backend.domain.identifiers import DeviceId, EspClaimId, EspDeviceId, ScenarioId, UserId
from backend.domain.personalization.dashboard_state import DashboardState
from backend.domain.personalization.dashboard_widget import DashboardWidget
from backend.domain.personalization.user_preferences import (
    InterfaceLanguage,
    TemperatureUnit,
    Theme,
    UserPreferences,
)
from backend.domain.personalization.widget_kind import WidgetKind
from backend.domain.scenarios.completion_behavior import CompletionBehavior
from backend.domain.scenarios.scenario import Scenario
from backend.domain.scenarios.scenario_action import ScenarioAction
from backend.domain.scenarios.scenario_status import ScenarioStatus
from backend.infrastructure.database.tables import (
    AutomationParticipantRow,
    AutomationRow,
    Base,
    BoardNetworkRow,
    DashboardRow,
    DashboardWidgetRow,
    DeviceCapabilityRow,
    DeviceRow,
    EspClaimRow,
    EspDeviceRow,
    PreferencesRow,
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
    UserRow,
)


def row_values(table: Table, row: Base) -> dict[str, object]:
    """Return the column values of a row as a plain mapping.

    The repositories write through Core statements rather than through the object
    graph of the session, so a mapped instance has to be flattened first. Keeping
    that here means no repository has to know which columns a table happens to
    have.

    Args:
        table: Table the row belongs to.
        row: Row to flatten.

    Returns:
        dict[str, object]: Column name mapped to its value.
    """
    return {column.name: getattr(row, column.name) for column in table.columns}


def as_utc(value: datetime) -> datetime:
    """Return a timestamp that is guaranteed to carry a time zone.

    A store may hand back a naive timestamp for a column declared with a time
    zone, and comparing that with an aware moment raises. Normalizing once, in
    the only place that builds aggregates, keeps the callers free of the concern.

    Args:
        value: Timestamp read from the store.

    Returns:
        datetime: The same moment, in UTC when the value arrived naive.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def user_to_row(user: User) -> UserRow:
    """Build the row describing an account.

    Args:
        user: Account to serialize.

    Returns:
        UserRow: New row describing the account.
    """
    return UserRow(
        id=user.id.value,
        email=user.email.value,
        password_hash=user.password_hash,
        display_name=user.display_name.value,
        created_at=user.created_at,
    )


def user_from_row(row: UserRow) -> User:
    """Build the account a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        User: Restored account.
    """
    return User(
        id=UserId.parse(row.id),
        email=Email(row.email),
        password_hash=row.password_hash,
        display_name=DisplayName(row.display_name),
        created_at=as_utc(row.created_at),
    )


def preferences_to_row(preferences: UserPreferences) -> PreferencesRow:
    """Build the row describing the interface preferences of an account.

    Args:
        preferences: Preferences to serialize.

    Returns:
        PreferencesRow: New row describing the preferences.
    """
    return PreferencesRow(
        user_id=preferences.user_id.value,
        temperature_unit=preferences.temperature_unit.value,
        theme=preferences.theme.value,
        language=preferences.language.value,
        show_command_chat=preferences.show_command_chat,
    )


def preferences_from_row(row: PreferencesRow) -> UserPreferences:
    """Build the preferences a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        UserPreferences: Restored preferences.
    """
    return UserPreferences(
        user_id=UserId.parse(row.user_id),
        temperature_unit=TemperatureUnit(row.temperature_unit),
        theme=Theme(row.theme),
        language=InterfaceLanguage(row.language),
        show_command_chat=row.show_command_chat,
    )


def dashboard_to_row(dashboard: DashboardState) -> DashboardRow:
    """Build the row marking that an account has a layout.

    Args:
        dashboard: Layout to serialize.

    Returns:
        DashboardRow: New row describing the owner of the layout.
    """
    return DashboardRow(user_id=dashboard.user_id.value)


def widget_rows(dashboard: DashboardState) -> list[DashboardWidgetRow]:
    """Build one row per entry of a dashboard layout.

    A layout entry has no identity of its own in the model, so the store assigns
    one. The render order is stored explicitly instead of being implied by an
    arbitrary primary key order.

    Args:
        dashboard: Layout to serialize.

    Returns:
        list[DashboardWidgetRow]: Rows in render order.
    """
    return [
        DashboardWidgetRow(
            id=uuid4(),
            user_id=dashboard.user_id.value,
            position=position,
            kind=widget.kind.value,
            device_id=None if widget.device_id is None else widget.device_id.value,
            title=widget.title,
        )
        for position, widget in enumerate(dashboard.widgets)
    ]


def dashboard_from_row(row: DashboardRow, widgets: list[DashboardWidgetRow]) -> DashboardState:
    """Build the layout a row and its widget rows describe.

    An entry whose device was deleted arrives without one. Such an entry cannot be
    drawn, so it is left out of the layout instead of being handed to the
    aggregate, which would refuse the whole layout over one dead reference.

    Args:
        row: Row identifying the owner of the layout.
        widgets: Widget rows belonging to that owner.

    Returns:
        DashboardState: Restored layout.
    """
    restored: list[DashboardWidget] = []
    for entry in sorted(widgets, key=lambda widget: widget.position):
        widget = widget_from_row(entry)
        if widget is not None:
            restored.append(widget)
    return DashboardState(user_id=UserId.parse(row.user_id), widgets=tuple(restored))


def widget_from_row(row: DashboardWidgetRow) -> DashboardWidget | None:
    """Build one layout entry, or None when it can no longer be drawn.

    Args:
        row: Row to deserialize.

    Returns:
        DashboardWidget | None: Restored entry, or None when the device it
        referenced is gone.
    """
    kind = WidgetKind.parse(row.kind)
    device_id = None if row.device_id is None else DeviceId.parse(row.device_id)
    if kind is WidgetKind.DEVICE and device_id is None:
        return None
    return DashboardWidget(kind=kind, device_id=device_id, title=row.title)


def device_to_row(device: Device) -> DeviceRow:
    """Build the row describing a logical device.

    Args:
        device: Device to serialize.

    Returns:
        DeviceRow: New row describing the device.
    """
    return DeviceRow(
        id=device.id.value,
        user_id=device.user_id.value,
        name=device.name,
        kind=device.kind.value,
        channel=int(device.channel),
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
    )


def device_from_row(row: DeviceRow, capabilities: frozenset[Capability]) -> Device:
    """Build the device a row and its capability rows describe.

    Args:
        row: Row to deserialize.
        capabilities: Capabilities read from ``device_capabilities``.

    Returns:
        Device: Restored device.
    """
    return Device(
        id=DeviceId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        name=row.name,
        kind=DeviceKind.parse(row.kind),
        channel=RelayChannel(row.channel),
        capabilities=capabilities,
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
    )


def capability_rows(device: Device) -> list[DeviceCapabilityRow]:
    """Build one row per capability of a logical device.

    Args:
        device: Device to serialize.

    Returns:
        list[DeviceCapabilityRow]: Capability rows of the device.
    """
    return [
        DeviceCapabilityRow(device_id=device.id.value, capability=capability.value)
        for capability in sorted(device.capabilities, key=lambda item: item.value)
    ]


def automation_to_row(settings: AutomationSettings) -> AutomationRow:
    """Build the row describing the automation configuration of an account.

    Args:
        settings: Configuration to serialize.

    Returns:
        AutomationRow: New row describing the configuration.
    """
    return AutomationRow(
        user_id=settings.user_id.value,
        enabled=settings.enabled,
        target_temperature=settings.target_temperature.celsius,
        temperature_tolerance=settings.temperature_tolerance,
        target_humidity=settings.target_humidity.percent,
        humidity_tolerance=settings.humidity_tolerance,
    )


def automation_from_row(
    row: AutomationRow, participants: frozenset[DeviceId]
) -> AutomationSettings:
    """Build the configuration a row and its participant rows describe.

    Args:
        row: Row to deserialize.
        participants: Devices read from ``automation_participants``.

    Returns:
        AutomationSettings: Restored configuration.
    """
    return AutomationSettings(
        user_id=UserId.parse(row.user_id),
        enabled=row.enabled,
        target_temperature=Temperature(row.target_temperature),
        temperature_tolerance=row.temperature_tolerance,
        target_humidity=Humidity(row.target_humidity),
        humidity_tolerance=row.humidity_tolerance,
        participating_device_ids=participants,
    )


def participant_rows(settings: AutomationSettings) -> list[AutomationParticipantRow]:
    """Build one row per device automation is allowed to drive.

    Args:
        settings: Configuration to serialize.

    Returns:
        list[AutomationParticipantRow]: Participant rows of the configuration.
    """
    return [
        AutomationParticipantRow(
            user_id=settings.user_id.value,
            device_id=device_id.value,
        )
        for device_id in sorted(settings.participating_device_ids, key=lambda item: item.value)
    ]


def scenario_to_row(scenario: Scenario) -> ScenarioRow:
    """Build the row describing a timed scenario.

    Args:
        scenario: Scenario to serialize.

    Returns:
        ScenarioRow: New row describing the scenario.
    """
    return ScenarioRow(
        id=scenario.id.value,
        user_id=scenario.user_id.value,
        status=scenario.status.value,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior.value,
    )


def scenario_from_row(
    row: ScenarioRow,
    actions: tuple[ScenarioAction, ...],
    captured_statuses: dict[DeviceId, DeviceStatus],
) -> Scenario:
    """Build the scenario a row and its collection rows describe.

    Args:
        row: Row to deserialize.
        actions: Actions read from ``scenario_actions``.
        captured_statuses: States read from ``scenario_captured_statuses``.

    Returns:
        Scenario: Restored scenario.
    """
    return Scenario(
        id=ScenarioId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        status=ScenarioStatus(row.status),
        created_at=as_utc(row.created_at),
        start_at=as_utc(row.start_at),
        duration_minutes=row.duration_minutes,
        target=row.target,
        completion_behavior=CompletionBehavior(row.completion_behavior),
        actions=actions,
        captured_statuses=captured_statuses,
    )


def action_rows(scenario: Scenario) -> list[ScenarioActionRow]:
    """Build one row per action of a scenario.

    An action names a capability and a target rather than a relay channel, and it
    has no identity of its own in the model, so the store assigns one and records
    the order explicitly.

    Args:
        scenario: Scenario to serialize.

    Returns:
        list[ScenarioActionRow]: Action rows in the order the scenario declares.
    """
    return [
        ScenarioActionRow(
            id=uuid4(),
            scenario_id=scenario.id.value,
            position=position,
            capability=action.capability.value,
            target_temperature=(
                None if action.target_temperature is None else action.target_temperature.celsius
            ),
        )
        for position, action in enumerate(scenario.actions)
    ]


def action_from_row(row: ScenarioActionRow) -> ScenarioAction:
    """Build the scenario action a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        ScenarioAction: Restored action.
    """
    return ScenarioAction(
        capability=Capability.parse(row.capability),
        target_temperature=(
            None if row.target_temperature is None else Temperature(row.target_temperature)
        ),
    )


def captured_status_rows(scenario: Scenario) -> list[ScenarioCapturedStatusRow]:
    """Build one row per device state captured before a scenario started.

    Args:
        scenario: Scenario to serialize.

    Returns:
        list[ScenarioCapturedStatusRow]: Captured state rows of the scenario.
    """
    return [
        ScenarioCapturedStatusRow(
            scenario_id=scenario.id.value,
            device_id=device_id.value,
            status=status.value,
        )
        for device_id, status in scenario.captured_statuses.items()
    ]


def captured_status_from_row(row: ScenarioCapturedStatusRow) -> tuple[DeviceId, DeviceStatus]:
    """Build the captured device state a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        tuple[DeviceId, DeviceStatus]: Device the state was captured for and the
        state itself.
    """
    return DeviceId.parse(row.device_id), DeviceStatus(row.status)


def board_to_row(board: EspDevice) -> EspDeviceRow:
    """Build the row describing a paired board.

    Args:
        board: Board to serialize.

    Returns:
        EspDeviceRow: New row describing the board.
    """
    return EspDeviceRow(
        id=board.id.value,
        user_id=board.user_id.value,
        name=board.name,
        pairing_key=board.pairing_key.value,
        created_at=board.created_at,
        last_seen_at=board.last_seen_at,
        current_ssid=board.current_ssid,
    )


def board_from_row(row: EspDeviceRow) -> EspDevice:
    """Build the board a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        EspDevice: Restored board.
    """
    return EspDevice(
        id=EspDeviceId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        name=row.name,
        pairing_key=PairingKey(row.pairing_key),
        created_at=as_utc(row.created_at),
        last_seen_at=None if row.last_seen_at is None else as_utc(row.last_seen_at),
        current_ssid=row.current_ssid,
    )


def claim_to_row(claim: EspClaim) -> EspClaimRow:
    """Build the row describing an announced board waiting for an owner.

    Args:
        claim: Offer to serialize.

    Returns:
        EspClaimRow: New row describing the offer.
    """
    return EspClaimRow(
        id=claim.id.value,
        device_key=claim.device_key.value,
        label=claim.label,
        claim_token=claim.claim_token,
        announced_at=claim.announced_at,
        expires_at=claim.expires_at,
        claimed_by=None if claim.claimed_by is None else claim.claimed_by.value,
    )


def claim_from_row(row: EspClaimRow) -> EspClaim:
    """Build the offer a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        EspClaim: Restored offer.
    """
    return EspClaim(
        id=EspClaimId.parse(row.id),
        device_key=PairingKey(row.device_key),
        label=row.label,
        claim_token=row.claim_token,
        announced_at=as_utc(row.announced_at),
        expires_at=as_utc(row.expires_at),
        claimed_by=None if row.claimed_by is None else UserId.parse(row.claimed_by),
    )


def network_to_row(network: BoardNetwork) -> BoardNetworkRow:
    """Build the row describing the network of a board.

    Args:
        network: Network to serialize.

    Returns:
        BoardNetworkRow: New row describing the network.
    """
    profile = network.profile
    return BoardNetworkRow(
        board_id=network.board_id.value,
        user_id=network.user_id.value,
        ssid=profile.ssid,
        password=profile.password,
        host=profile.host,
        server_port=profile.server_port,
        socket_port=profile.socket_port,
        socket_path=profile.socket_path,
        updated_at=network.updated_at,
    )


def network_from_row(row: BoardNetworkRow) -> BoardNetwork:
    """Build the network a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        BoardNetwork: Restored network.
    """
    return BoardNetwork(
        board_id=EspDeviceId.parse(row.board_id),
        user_id=UserId.parse(row.user_id),
        profile=NetworkProfile(
            ssid=row.ssid,
            password=row.password,
            host=row.host,
            server_port=row.server_port,
            socket_port=row.socket_port,
            socket_path=row.socket_path,
        ),
        updated_at=as_utc(row.updated_at),
    )
