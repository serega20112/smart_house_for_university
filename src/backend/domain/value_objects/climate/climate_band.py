"""Acceptable climate band implementing the hysteresis.

The band is stored as a target plus a tolerance rather than as two loose numbers,
because that is the only shape in which the pair cannot be transposed or turned
negative by a caller. A single constructor check replaces the defensive absolute
value calls that used to be sprinkled over every computation.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidToleranceError


@dataclass(frozen=True, slots=True)
class ClimateBand[MeasuredT]:
    """The acceptable band around a target value.

    Args:
        target: Value the home is asked to hold.
        tolerance: How far the measurement may drift before a device is driven.
            Never negative: the constructor refuses it, so no accessor has to
            repair it later.

    Returns:
        None.

    Raises:
        InvalidToleranceError: When the tolerance is negative.
    """

    target: MeasuredT
    tolerance: float

    def __post_init__(self) -> None:
        """Validate the tolerance.

        Returns:
            None.

        Raises:
            InvalidToleranceError: When the tolerance is negative.
        """
        if self.tolerance < 0:
            raise InvalidToleranceError(self.tolerance)

    @property
    def low(self) -> float:
        """Return the lower bound of the band.

        Returns:
            float: Lower bound.
        """
        return self._value_of(self.target) - self.tolerance

    @property
    def high(self) -> float:
        """Return the upper bound of the band.

        Returns:
            float: Upper bound.
        """
        return self._value_of(self.target) + self.tolerance

    def contains(self, measurement: MeasuredT) -> bool:
        """Return whether a measurement already sits inside the band.

        Args:
            measurement: Value measured by the sensors.

        Returns:
            bool: True when nothing has to be changed.
        """
        numeric = self._value_of(measurement)
        return self.low <= numeric <= self.high

    def needs_increase(self, measurement: MeasuredT) -> bool:
        """Return whether a measurement is below the band.

        Args:
            measurement: Value measured by the sensors.

        Returns:
            bool: True when heating or humidifying is required.
        """
        return self._value_of(measurement) < self.low

    def needs_decrease(self, measurement: MeasuredT) -> bool:
        """Return whether a measurement is above the band.

        Args:
            measurement: Value measured by the sensors.

        Returns:
            bool: True when cooling or drying is required.
        """
        return self._value_of(measurement) > self.high

    @staticmethod
    def _value_of(measurement: MeasuredT) -> float:
        if isinstance(measurement, bool):
            raise TypeError("a boolean is not a climate measurement")
        if isinstance(measurement, (int, float)):
            return float(measurement)
        celsius = getattr(measurement, "celsius", None)
        if celsius is not None:
            return float(celsius)
        percent = getattr(measurement, "percent", None)
        if percent is not None:
            return float(percent)
        return float(measurement)  # type: ignore[arg-type]
