"""Credentials presented at login."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticateCommand:
    """Credentials the person presented to sign in.

    Args:
        email: Login of the account.
        password: Plain password.

    Returns:
        None.
    """

    email: str
    password: str
