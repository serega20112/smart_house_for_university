"""Данные, нужные для авторизации входа, и ничего больше."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import UserId


@dataclass(frozen=True, slots=True)
class StoredCredentials:
    """Пара: идентификатор аккаунта и хранимая форма его пароля.

    Отображаемого имени здесь нет, как и пароля в открытом виде: читающему для
    входа нужны ровно эти два поля.

    Attributes:
        user_id: Аккаунт, к которому относятся данные.
        password_hash: Хранимая форма пароля.
    """

    user_id: UserId
    password_hash: str
