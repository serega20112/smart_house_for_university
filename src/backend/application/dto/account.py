"""Contracts of the account operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import UserId


@dataclass(frozen=True, slots=True)
class RegisterAccountCommand:
    """What a person typed to create an account.

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


@dataclass(frozen=True, slots=True)
class AuthenticateCommand:
    """Credentials presented at login.

    Args:
        email: Login of the account.
        password: Plain password.

    Returns:
        None.
    """

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class AccountProfile:
    """What the interface is allowed to know about an account.

    The stored password has no field here on purpose: a profile is shown to a
    person, and a secret must never travel towards a screen.

    Args:
        id: Identifier of the account.
        email: Login of the account.
        display_name: Name shown in the interface.
        created_at: Moment the account was created.

    Returns:
        None.
    """

    id: UserId
    email: str
    display_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """An account together with the session that was opened for it.

    Args:
        profile: Profile of the signed in account.
        token: Session token to send with every following request.
        expires_at: Moment the token stops being accepted.

    Returns:
        None.
    """

    profile: AccountProfile
    token: str
    expires_at: datetime
