"""Аккаунт в том виде, в каком его разрешено показывать."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import UserId


@dataclass(frozen=True, slots=True)
class AccountProfile:
    """Публичная часть аккаунта.

    Поля для пароля здесь нет намеренно: профиль показывают человеку, а секрет
    не должен путешествовать к экрану.

    Attributes:
        id: Идентификатор аккаунта.
        email: Логин аккаунта.
        display_name: Имя, которое видно в интерфейсе.
        created_at: Момент создания аккаунта.
    """

    id: UserId
    email: str
    display_name: str
    created_at: datetime
