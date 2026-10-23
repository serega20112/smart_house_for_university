"""Мапперы настроек автоматизации и участия устройств."""

from __future__ import annotations

from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature
from backend.infrastructure.database.tables import (
    AutomationParticipantRow,
    AutomationRow,
)


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
        version=settings.version,
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
        version=row.version,
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
