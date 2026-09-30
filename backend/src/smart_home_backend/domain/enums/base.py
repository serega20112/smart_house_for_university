"""Base string enum for domain enumerations."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Enum whose members compare and serialize as plain strings.

    Args:
        None.

    Returns:
        str: Member value.
    """

    def __str__(self) -> str:
        """Return the string value of the member.

        Returns:
            str: Member value.
        """
        return self.value
