"""Строка аккаунта.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.tables.base import Base


class UserRow(Base):
    """Stored account of one person.

    Args:
        id: Identifier assigned by the domain aggregate.
        email: Normalized login, unique across the whole system.
        password_hash: Stored form of the password, produced by the hasher and
            never inspected by the model.
        display_name: Name shown in the interface.
        created_at: Moment the account was created.

    Returns:
        None.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
