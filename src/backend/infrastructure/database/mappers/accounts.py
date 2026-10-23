"""Mapping between the account aggregate and the user row."""

from __future__ import annotations

from backend.domain.aggregates.user.user import User
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.tables import UserRow


def user_to_row(user: User) -> UserRow:
    """Build the row describing an account.

    Args:
        user: Account to serialize.

    Returns:
        UserRow: New row describing the account.
    """
    return UserRow(
        id=user.id.value,
        email=user.email.value,
        display_name=user.display_name.value,
        password_hash=user.password_hash,
        created_at=user.created_at,
        version=user.version,
    )


def user_from_row(row: UserRow) -> User:
    """Build the account a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        User: Restored account.
    """
    return User(
        id=UserId.parse(row.id),
        email=Email.parse(row.email),
        display_name=DisplayName.parse(row.display_name),
        password_hash=row.password_hash,
        created_at=as_utc(row.created_at),
        version=row.version,
    )
