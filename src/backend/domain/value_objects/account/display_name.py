"""Name shown in the interface for an account."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidDisplayNameError

MAX_LENGTH = 80


@dataclass(frozen=True, slots=True, order=True)
class DisplayName:
    """A name a person wants to be called by.

    Args:
        value: Trimmed name.

    Returns:
        None.

    Raises:
        InvalidDisplayNameError: When the name is empty or too long.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the name.

        Returns:
            None.

        Raises:
            InvalidDisplayNameError: When the name is empty or too long.
        """
        trimmed = self.value.strip()
        if not trimmed:
            raise InvalidDisplayNameError("is empty")
        if len(trimmed) > MAX_LENGTH:
            raise InvalidDisplayNameError(f"is longer than {MAX_LENGTH} characters")
        object.__setattr__(self, "value", trimmed)

    @classmethod
    def parse(cls, raw: str) -> DisplayName:
        """Build a display name from what a person typed.

        Args:
            raw: Raw text entered by the user.

        Returns:
            DisplayName: Trimmed name.

        Raises:
            InvalidDisplayNameError: When the text is not a usable name.
        """
        return cls(raw)
