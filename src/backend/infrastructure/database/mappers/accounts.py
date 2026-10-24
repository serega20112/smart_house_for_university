"""Перевод аккаунта туда и обратно в строку пользователя."""

from __future__ import annotations

from backend.domain.aggregates.user.user import User
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import UserModel


def user_to_row(user: User) -> UserModel:
    """Строит строку, описывающую аккаунт."""
    return UserModel(
        id=user.id.value,
        email=user.email.value,
        display_name=user.display_name.value,
        password_hash=user.password_hash,
        created_at=user.created_at,
    )


def user_from_row(row: UserModel) -> User:
    """Строит аккаунт, описанный строкой."""
    return User(
        id=UserId.parse(row.id),
        email=Email.parse(row.email),
        display_name=DisplayName.parse(row.display_name),
        password_hash=row.password_hash,
        created_at=as_utc(row.created_at),
    )
