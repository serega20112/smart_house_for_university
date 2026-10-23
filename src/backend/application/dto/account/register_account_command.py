"""What a person typed to create an account."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterAccountCommand:
    """A new account the interface was asked to create.

    Args:
        email: Login the person chose.
        display_name: Name they want to be called by.
        password: Plain password, which never leaves this object.

    Returns:
        None.
    """

    email: str
    display_name: str
    password: str
