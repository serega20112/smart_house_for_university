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

from backend.infrastructure.database.models.base import Base


class UserModel(Base):
    """Сохранённый аккаунт одного человека.

    Attributes:
        id: Идентификатор, выданный агрегатом домена.
        email: Приведённый логин, один на всю систему.
        password_hash: Сохранённая форма пароля, построенная хешером и никогда не
            разбираемая моделью.
        display_name: Имя, показанное в интерфейсе.
        created_at: Момент создания аккаунта.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
