"""Читающая сторона аккаунтов.

Чтение аккаунта не открывает транзакцию. Модели чтения подогнаны под своего
потребителя: профиль для интерфейса, где нет поля для хранимого пароля, и пара
данных для входа, где нет поля для отображаемого имени.
"""

from __future__ import annotations

from typing import Protocol

from backend.application.dto.views.account_profile import AccountProfile
from backend.application.dto.views.auth_record import AuthRecord
from backend.domain.identifiers import UserId


class AccountQueries(Protocol):
    """Чтения аккаунтов."""

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Возвращает профиль аккаунта."""

    async def get_auth_record(self, email: str) -> AuthRecord | None:
        """Возвращает учётные данные и профиль аккаунта под этим логином."""

    async def list_registered_ids(self) -> list[UserId]:
        """Возвращает идентификаторы всех зарегистрированных аккаунтов.

        Фоновым циклам нужно обслуживать каждый дом, но сам цикл целиком живёт в
        пределах одного аккаунта.
        """
