"""User account.

The aggregate owns the rules about what an account may look like. It does not own
hashing: that is cryptography, it lives in the infrastructure layer behind a port,
and the aggregate only stores the resulting string it was handed.

Registering an account is also the moment the rest of the home has to come into
existence, so the aggregate records that fact and lets whoever is subscribed set
the home up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from backend.domain.events import UserRegistered
from backend.domain.exceptions import WeakPasswordError
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email

MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True, slots=True)
class User:
    """One person using the platform.

    Args:
        id: Identifier of the account.
        email: Login of the account.
        password_hash: Stored form of the password, produced by the password
            hasher and never inspected by the model.
        display_name: Name shown in the interface.
        created_at: Moment the account was created.
        _events: Facts recorded since the account was loaded.

    Returns:
        None.
    """

    id: UserId
    email: Email
    password_hash: str
    display_name: DisplayName
    created_at: datetime
    _events: list[UserRegistered] = field(default_factory=list, repr=False, compare=False)

    @property
    def can_authenticate_with(self) -> str:
        """Return the stored password to compare a presented one against.

        The aggregate hands the value over instead of comparing it: hashing is
        infrastructure work, and the model refuses to grow a cryptography
        dependency.

        Returns:
            str: Stored password form.
        """
        return self.password_hash

    def pull_events(self) -> tuple[UserRegistered, ...]:
        """Return the recorded facts and forget them.

        Returns:
            tuple[UserRegistered, ...]: Facts recorded since the last call.
        """
        recorded = tuple(self._events)
        object.__setattr__(self, "_events", [])
        return recorded

    @classmethod
    def register(
        cls,
        email: Email,
        display_name: DisplayName,
        password_hash: str,
        password_length: int,
        created_at: datetime,
    ) -> Self:
        """Create a new account.

        Args:
            email: Login of the account.
            display_name: Name shown in the interface.
            password_hash: Stored form of the password.
            password_length: Length of the password the person chose, which the
                model refuses to be too short of.
            created_at: Moment the account was created.

        Returns:
            Self: Created account.

        Raises:
            WeakPasswordError: When the password is shorter than allowed.
        """
        if password_length < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(MIN_PASSWORD_LENGTH)
        user = cls(
            id=UserId.generate(),
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            created_at=created_at,
        )
        user._events.append(UserRegistered(user_id=user.id))
        return user
