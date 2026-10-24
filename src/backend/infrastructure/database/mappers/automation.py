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
    """Строит строку, описывающую настройку автоматизации аккаунта."""
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
    """Строит настройку, описанную её строкой и строками участников.

    Args:
        participants: Устройства, прочитанные из ``automation_participants``.
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
    """Строит по строке на каждое устройство, которым автоматизации разрешено управлять.

    Порядок участников задают явно, иначе файл с перечислением unset-значений в
    множестве менялся бы от запуска к запуску.
    """
    return [
        AutomationParticipantRow(
            user_id=settings.user_id.value,
            device_id=device_id.value,
        )
        for device_id in sorted(settings.participating_device_ids, key=lambda item: item.value)
    ]
