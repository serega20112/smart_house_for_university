"""Temperature value object."""

from __future__ import annotations

from dataclasses import dataclass

MIN_CELSIUS = -40.0
MAX_CELSIUS = 80.0


@dataclass(frozen=True, slots=True)
class Temperature:
    """Immutable temperature value in degrees Celsius.

    Args:
        celsius: Temperature value.

    Returns:
        None.

    Raises:
        ValueError: When the value is outside the physically valid range.
    """

    celsius: float

    def __post_init__(self) -> None:
        """Validate the temperature range.

        Returns:
            None.

        Raises:
            ValueError: When the value is outside the valid range.
        """
        if not MIN_CELSIUS <= self.celsius <= MAX_CELSIUS:
            raise ValueError(f"temperature out of range: {self.celsius}")

    def with_delta(self, delta: float) -> "Temperature":
        """Return a shifted temperature.

        Args:
            delta: Offset in degrees Celsius.

        Returns:
            Temperature: Shifted value.
        """
        return Temperature(self.celsius + delta)

    def __str__(self) -> str:
        """Return the human readable form of the value.

        Returns:
            str: Formatted temperature.
        """
        return f"{self.celsius:.1f}°C"
