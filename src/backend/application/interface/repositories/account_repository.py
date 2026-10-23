"""Хранилище аккаунтов системы.

Аккаунт — корень области видимости, поэтому он сам и есть ключ: искать его «в
пределах аккаунта» не нужно, и этот репозиторий не наследует операции с владельцем.
"""

from __future__ import annotations

from abc import abstractmethod

from backend.application.interface.repositories.base import Creator
from backend.domain.aggregates.user.user import User
from backend.domain.identifiers import UserId


class AccountRepository(Creator[User]):
    """Хранилище аккаунтов."""

    @abstractmethod
    async def get(self, user_id: UserId) -> User | None:
        """Возвращает аккаунт по идентификатору или None, если его нет."""
