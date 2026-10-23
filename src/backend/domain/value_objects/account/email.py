"""Login of an account.

The login is self validating: an account cannot be built around a value the model
would refuse, so no use case has to remember to call a validator before saving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.domain.exceptions import InvalidEmailError

PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_LENGTH = 254


@dataclass(frozen=True, slots=True, order=True)
class Email:
    """A normalized login.

    Args:
        value: Lowercase address without surrounding spaces.

    Returns:
        None.

    Raises:
        InvalidEmailError: When the value is empty, too long or malformed.
    """

    value: str

    def __post_init__(self) -> None:
        """Normalize and validate the login.

        Returns:
            None.

        Raises:
            InvalidEmailError: When the value is empty, too long or malformed.
        """
        normalized = self.value.strip().lower()
        if not normalized:
            raise InvalidEmailError("is empty")
        if len(normalized) > MAX_LENGTH:
            raise InvalidEmailError(f"is longer than {MAX_LENGTH} characters")
        if not PATTERN.match(normalized):
            raise InvalidEmailError("does not look like an address")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def parse(cls, raw: str) -> Email:
        """Build a login from what a person typed.

        Args:
            raw: Raw text entered by the user.

        Returns:
            Email: Normalized login.

        Raises:
            InvalidEmailError: When the text is not a usable login.
        """
        return cls(raw)
