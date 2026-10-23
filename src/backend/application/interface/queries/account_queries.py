"""Читающая сторона аккаунтов.

Чтение аккаунта не открывает транзакцию. Модели чтения подогнаны под своего
потребителя: профиль для интерфейса, где нет поля для хранимого пароля, и пара
данных для входа, где нет поля для отображаемого имени.
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.account_profile import AccountProfile
from backend.domain.value_objects.account.stored_credentials import StoredCredentials


class AccountQueries(Protocol):
    """Чтения аккаунтов."""

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Возвращает профиль аккаунта."""

    async def get_credentials(self, email: str) -> StoredCredentials | None:
        """Возвращает данные входа, к которому относится логин."""

    async def list_registered_ids(self) -> list[UserId]:
        """Возвращает идентификаторы всех зарегистрированных аккаунтов.

        Фоновым циклам нужно обслуживать каждый дом, но сам цикл целиком живёт в
        пределах одного аккаунта.
        """
