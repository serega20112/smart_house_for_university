"""Automation configuration of one account.

The settings are an aggregate of their own: they own the target, the tolerance
around it and the list of devices taking part. Every change goes through a method
that validates and records the fact, so a use case cannot switch a flag by
assigning to it and cannot build an unachievable band.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from backend.domain.events import AutomationSettingsChanged
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.climate_band import ClimateBand
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.climate.tolerance import Tolerance

DEFAULT_TARGET_TEMPERATURE_C = 22.0
DEFAULT_TEMPERATURE_TOLERANCE_C = 1.0
DEFAULT_TARGET_HUMIDITY_PERCENT = 45.0
DEFAULT_HUMIDITY_TOLERANCE_PERCENT = 5.0


@dataclass
class AutomationSettings:
    """Targets and tolerances the climate automation aims for.

    Args:
        user_id: Owner of the configuration.
        enabled: Whether automation is active.
        target_temperature: Temperature the home is asked to hold.
        temperature_tolerance: How far the temperature may drift before a device
            is driven.
        target_humidity: Humidity the home is asked to hold.
        humidity_tolerance: How far the humidity may drift.
        participating_device_ids: Devices taking part; an empty set means every
            device that opted in.

    Returns:
        None.
    """

    user_id: UserId
    enabled: bool = False
    target_temperature: Temperature = field(
        default_factory=lambda: Temperature(DEFAULT_TARGET_TEMPERATURE_C)
    )
    temperature_tolerance: float = DEFAULT_TEMPERATURE_TOLERANCE_C
    target_humidity: Humidity = field(
        default_factory=lambda: Humidity(DEFAULT_TARGET_HUMIDITY_PERCENT)
    )
    humidity_tolerance: float = DEFAULT_HUMIDITY_TOLERANCE_PERCENT
    participating_device_ids: frozenset[DeviceId] = field(default_factory=frozenset)
    version: int = 0
    _events: list[AutomationSettingsChanged] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Validate both tolerances so no accessor has to repair them later.

        Returns:
            None.

        Raises:
            InvalidToleranceError: When a tolerance is negative or too large.
        """
        Tolerance(self.temperature_tolerance)
        Tolerance(self.humidity_tolerance)

    @property
    def temperature_band(self) -> ClimateBand[Temperature]:
        """Return the acceptable temperature band.

        Returns:
            ClimateBand[Temperature]: Band around the target temperature.
        """
        return ClimateBand(self.target_temperature, self.temperature_tolerance)

    @property
    def humidity_band(self) -> ClimateBand[Humidity]:
        """Return the acceptable humidity band.

        Returns:
            ClimateBand[Humidity]: Band around the target humidity.
        """
        return ClimateBand(self.target_humidity, self.humidity_tolerance)

    def device_participates(self, device_id: DeviceId) -> bool:
        """Return whether automation may drive a device.

        Args:
            device_id: Identifier of the device.

        Returns:
            bool: True when the device takes part in automation.
        """
        if not self.participating_device_ids:
            return True
        return device_id in self.participating_device_ids

    def enable(self) -> None:
        """Turn automation on.

        Returns:
            None.
        """
        self._set_enabled(True)

    def disable(self) -> None:
        """Turn automation off.

        Returns:
            None.
        """
        self._set_enabled(False)

    def aim_at_temperature(self, target: Temperature, tolerance: float | None = None) -> None:
        """Change the temperature the home is asked to hold.

        The new values are validated before they are stored, so a refused
        tolerance leaves the configuration exactly as it was.

        Args:
            target: New target temperature.
            tolerance: New tolerance or None to keep the current one.

        Returns:
            None.

        Raises:
            InvalidToleranceError: When the new tolerance is negative or too large.
        """
        checked = self._checked_tolerance(tolerance, self.temperature_tolerance)
        self.target_temperature = target
        self.temperature_tolerance = checked
        self._record()

    def aim_at_humidity(self, target: Humidity, tolerance: float | None = None) -> None:
        """Change the humidity the home is asked to hold.

        The new values are validated before they are stored, so a refused
        tolerance leaves the configuration exactly as it was.

        Args:
            target: New target humidity.
            tolerance: New tolerance or None to keep the current one.

        Returns:
            None.

        Raises:
            InvalidToleranceError: When the new tolerance is negative or too large.
        """
        checked = self._checked_tolerance(tolerance, self.humidity_tolerance)
        self.target_humidity = target
        self.humidity_tolerance = checked
        self._record()

    def set_participants(self, device_ids: frozenset[DeviceId]) -> None:
        """Choose the devices automation is allowed to drive.

        Args:
            device_ids: Participants, or an empty set for every opted in device.

        Returns:
            None.
        """
        self.participating_device_ids = frozenset(device_ids)
        self._record()

    def pull_events(self) -> tuple[AutomationSettingsChanged, ...]:
        """Return the recorded facts and forget them.

        Returns:
            tuple[AutomationSettingsChanged, ...]: Facts recorded since the last call.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def _set_enabled(self, enabled: bool) -> None:
        if self.enabled is enabled:
            return
        self.enabled = enabled
        self._record()

    @staticmethod
    def _checked_tolerance(requested: float | None, current: float) -> float:
        """Return a tolerance that is known to be acceptable.

        Args:
            requested: Tolerance the caller asked for, or None to keep the
                current one.
            current: Tolerance stored right now.

        Returns:
            float: Validated width of the band.

        Raises:
            InvalidToleranceError: When the requested tolerance is negative or
                too large.
        """
        if requested is None:
            return Tolerance(current).value
        return Tolerance(requested).value

    def _record(self) -> None:
        self._events.append(AutomationSettingsChanged(user_id=self.user_id))

    @classmethod
    def create(cls, user_id: UserId) -> Self:
        """Build the configuration a fresh account starts with.

        Args:
            user_id: Owner of the configuration.

        Returns:
            Self: Default configuration with automation switched off.
        """
        return cls(user_id=user_id)
