"""How far a measurement may drift from its target.

A tolerance is a value object rather than a bare number, because a negative
tolerance is not a small tolerance: it is a band that can never be reached and
its sign is easy to lose while it travels through a use case. The object refuses
an impossible value once, at construction, and carries it afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidToleranceError

MAX_TOLERANCE = 50.0
"""Largest tolerance any measured value may carry."""


@dataclass(frozen=True, slots=True)
class Tolerance:
    """How far a measurement may drift from its target.

    Attributes:
        value: Width of the tolerated band, never negative.

    """

    value: float

    def __post_init__(self) -> None:
        """Validate the width of the band.

        Returns:
            None.

        Raises:
            InvalidToleranceError: When the width is negative or too large.
        """
        if self.value < 0:
            raise InvalidToleranceError(self.value)
        if self.value > MAX_TOLERANCE:
            raise InvalidToleranceError(self.value)

    def __float__(self) -> float:
        """Return the width of the band.

        Returns:
            float: Width of the band.
        """
        return self.value
