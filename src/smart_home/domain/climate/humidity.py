"""Relative humidity value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from smart_home.domain.exceptions import InvalidHumidityError

MIN_PERCENT = 0.0
MAX_PERCENT = 100.0


@dataclass(frozen=True, slots=True, order=True)
class Humidity:
    """A relative humidity in percent.

    Args:
        percent: Measured or requested value.

    Returns:
        None.

    Raises:
        InvalidHumidityError: When the value is outside the valid range.
    """

    percent: float

    def __post_init__(self) -> None:
        """Validate the range of the value.

        Returns:
            None.

        Raises:
            InvalidHumidityError: When the value is outside the range.
        """
        if not MIN_PERCENT <= self.percent <= MAX_PERCENT:
            raise InvalidHumidityError(self.percent)

    def shifted_by(self, delta: float) -> Self:
        """Return the humidity a number of percent away, clamped to the range.

        Args:
            delta: Offset in percent.

        Returns:
            Self: Shifted value.
        """
        clamped = min(MAX_PERCENT, max(MIN_PERCENT, self.percent + delta))
        return type(self)(clamped)

    def distance_to(self, other: Humidity) -> float:
        """Return how far this value lies from another one.

        Args:
            other: Value to measure the distance to.

        Returns:
            float: Absolute difference in percent.
        """
        return abs(self.percent - other.percent)
