"""Contracts of the automation operations."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.climate.humidity import Humidity
from backend.domain.climate.temperature import Temperature
from backend.domain.identifiers import DeviceId


@dataclass(frozen=True, slots=True)
class AutomationPatch:
    """Partial change of the automation configuration.

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


@dataclass(frozen=True, slots=True)
class AutomationView:
    """The automation configuration as the interface needs it.

    Args:
        enabled: Whether automation is active.
        target_temperature: Temperature the home is asked to hold.
        temperature_tolerance: How far the temperature may drift.
        target_humidity: Humidity the home is asked to hold.
        humidity_tolerance: How far the humidity may drift.
        participating_device_ids: Devices automation is allowed to drive.

    Returns:
        None.
    """

    enabled: bool
    target_temperature: float
    target_humidity: float
    temperature_tolerance: float
    humidity_tolerance: float
    participating_device_ids: frozenset[DeviceId]


@dataclass(frozen=True, slots=True)
class AutomationCycleReport:
    """What one automation cycle did.

    Args:
        performed: Demands that were carried out, empty when nothing was needed.
        skipped_reason: Why the cycle did nothing, or None when it acted.

    Returns:
        None.
    """

    performed: tuple[str, ...] = ()
    skipped_reason: str | None = None
