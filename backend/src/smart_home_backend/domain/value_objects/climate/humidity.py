"""Humidity value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Humidity:
    """Immutable relative humidity value in percent.

    Args:
        percent: Relative humidity.

    Returns:
        None.

    Raises:
        ValueError: When the value is outside the zero to one hundred range.
    """

    percent: float

    def __post_init__(self) -> None:
        """Validate the humidity range.

        Returns:
            None.

        Raises:
            ValueError: When the value is outside the valid range.
        """
        if not 0.0 <= self.percent <= 100.0:
            raise ValueError(f"humidity out of range: {self.percent}")

    def with_delta(self, delta: float) -> "Humidity":
        """Return a shifted humidity clamped to the valid range.

        Args:
            delta: Offset in percent.

        Returns:
            Humidity: Shifted value.
        """
        return Humidity(min(100.0, max(0.0, self.percent + delta)))

    def __str__(self) -> str:
        """Return the human readable form of the value.

        Returns:
            str: Formatted humidity.
        """
        return f"{self.percent:.0f}%"
