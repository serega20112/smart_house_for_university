"""Mappers between domain entities and database rows.

Enum and JSON serialization is isolated here, which keeps the domain free of any
persistence concern.
"""

from __future__ import annotations

from datetime import datetime, timezone

from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction
from smart_home_backend.domain.enums.device import Capability, parse_device_type
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus
from smart_home_backend.infrastructure.database.models import (
    AUTOMATION_SINGLETON_ID,
    AutomationRow,
    DeviceRow,
    ScenarioRow,
)


def device_to_row(device: Device) -> DeviceRow:
    """Build a database row from a device.

    Args:
        device: Device to serialize.

    Returns:
        DeviceRow: New row describing the device.
    """
    return DeviceRow(
        id=device.id or None,
        name=device.name,
        type=device.type.value,
        physical_channel=device.physical_channel,
        capabilities=sorted(capability.value for capability in device.capabilities),
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
    )


def device_from_row(row: DeviceRow) -> Device:
    """Build a device from a database row.

    Args:
        row: Row to deserialize.

    Returns:
        Device: Restored device.
    """
    return Device(
        id=row.id,
        name=row.name,
        type=parse_device_type(row.type),
        physical_channel=row.physical_channel,
        capabilities=frozenset(Capability(name) for name in (row.capabilities or [])),
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
    )


def automation_to_row(settings: AutomationSettings) -> AutomationRow:
    """Build a database row from automation settings.

    Args:
        settings: Settings to serialize.

    Returns:
        AutomationRow: New row describing the settings.
    """
    return AutomationRow(
        id=AUTOMATION_SINGLETON_ID,
        enabled=settings.enabled,
        target_temperature=settings.target_temperature,
        temperature_tolerance=settings.temperature_tolerance,
        target_humidity=settings.target_humidity,
        humidity_tolerance=settings.humidity_tolerance,
        participating_device_ids=sorted(settings.participating_device_ids),
    )


def automation_from_row(row: AutomationRow) -> AutomationSettings:
    """Build automation settings from a database row.

    Args:
        row: Row to deserialize.

    Returns:
        AutomationSettings: Restored settings.
    """
    return AutomationSettings(
        enabled=row.enabled,
        target_temperature=row.target_temperature,
        temperature_tolerance=row.temperature_tolerance,
        target_humidity=row.target_humidity,
        humidity_tolerance=row.humidity_tolerance,
        participating_device_ids=frozenset(row.participating_device_ids or []),
    )


def scenario_to_row(scenario: Scenario) -> ScenarioRow:
    """Build a database row from a scenario.

    Args:
        scenario: Scenario to serialize.

    Returns:
        ScenarioRow: New row describing the scenario.
    """
    return ScenarioRow(
        id=scenario.id or None,
        status=scenario.status.value,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        actions=[action.to_dict() for action in scenario.actions],
        completion_behavior=scenario.completion_behavior.value,
        restore_snapshot={
            str(device_id): value for device_id, value in scenario.restore_snapshot.items()
        },
    )


def scenario_from_row(row: ScenarioRow) -> Scenario:
    """Build a scenario from a database row.

    Args:
        row: Row to deserialize.

    Returns:
        Scenario: Restored scenario.
    """
    return Scenario(
        id=row.id,
        status=ScenarioStatus(row.status),
        created_at=_as_utc(row.created_at),
        start_at=_as_utc(row.start_at),
        actions=[ScenarioAction.from_dict(action) for action in (row.actions or [])],
        target=row.target,
        duration_minutes=row.duration_minutes,
        completion_behavior=CompletionBehavior(row.completion_behavior),
        restore_snapshot={
            int(device_id): value for device_id, value in (row.restore_snapshot or {}).items()
        },
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
