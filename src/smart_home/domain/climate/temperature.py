"""Temperature value object.

The model refuses to hold a temperature it cannot believe, so a use case never
compares raw numbers against the physical limits and never reports an out of range
value it accepted a moment earlier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from smart_home.domain.exceptions import InvalidTemperatureError

MIN_CELSIUS = -40.0
MAX_CELSIUS = 80.0


@dataclass(frozen=True, slots=True, order=True)
class Temperature:
    """A temperature in degrees Celsius.

    Args:
        celsius: Measured or requested value.

    Returns:
        None.

    Raises:
        InvalidTemperatureError: When the value is outside the physical range.
    """

    celsius: float

    def __post_init__(self) -> None:
        """Validate the physical range of the value.

        Returns:
            None.

        Raises:
            InvalidTemperatureError: When the value is outside the range.
        """
        if not MIN_CELSIUS <= self.celsius <= MAX_CELSIUS:
            raise InvalidTemperatureError(self.celsius)

    def shifted_by(self, delta: float) -> Self:
        """Return the temperature a number of degrees away from this one.

        Args:
            delta: Offset in degrees Celsius.

        Returns:
            Self: Shifted value.
        """
        return type(self)(self.celsius + delta)

    def distance_to(self, other: Temperature) -> float:
        """Return how far this value lies from another one.

        Args:
            other: Value to measure the distance to.

        Returns:
            float: Absolute difference in degrees Celsius.
        """
        return abs(self.celsius - other.celsius)
