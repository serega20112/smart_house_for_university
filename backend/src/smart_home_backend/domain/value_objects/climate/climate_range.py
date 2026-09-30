"""Acceptable climate band implementing the hysteresis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClimateRange:
    """Acceptable band around a target, expressed as target plus tolerance.

    Keeping the band around the target is what stops a device from switching on
    and off around a single threshold value.

    Args:
        target: Target value.
        tolerance: Symmetric tolerance around the target.

    Returns:
        None.
    """

    target: float
    tolerance: float

    @property
    def low(self) -> float:
        """Return the lower bound of the band.

        Returns:
            float: Lower bound.
        """
        return self.target - abs(self.tolerance)

    @property
    def high(self) -> float:
        """Return the upper bound of the band.

        Returns:
            float: Upper bound.
        """
        return self.target + abs(self.tolerance)

    def contains(self, value: float) -> bool:
        """Return whether a value lies inside the band.

        Args:
            value: Measured value.

        Returns:
            bool: True when nothing has to be changed.
        """
        return self.low <= value <= self.high

    def needs_increase(self, value: float) -> bool:
        """Return whether a value is below the band.

        Args:
            value: Measured value.

        Returns:
            bool: True when heating or humidifying is required.
        """
        return value < self.low

    def needs_decrease(self, value: float) -> bool:
        """Return whether a value is above the band.

        Args:
            value: Measured value.

        Returns:
            bool: True when cooling or drying is required.
        """
        return value > self.high
