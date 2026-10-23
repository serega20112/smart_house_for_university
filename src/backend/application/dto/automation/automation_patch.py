"""A partial change of the automation configuration."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature


@dataclass(frozen=True, slots=True)
class AutomationPatch:
    """The fields of the automation configuration a person wants to change.

    Every field is optional and None means "keep", which is what lets one use case
    serve the whole configuration instead of a family of near identical ones
    differing by a single number.

    Args:
        enabled: New automation flag or None.
        target_temperature: New target temperature or None.
        temperature_tolerance: New temperature tolerance or None.
        target_humidity: New target humidity or None.
        humidity_tolerance: New humidity tolerance or None.
        participating_device_ids: New participants or None.

    Returns:
        None.
    """

    enabled: bool | None = None
    target_temperature: Temperature | None = None
    temperature_tolerance: float | None = None
    target_humidity: Humidity | None = None
    humidity_tolerance: float | None = None
    participating_device_ids: frozenset[DeviceId] | None = None
