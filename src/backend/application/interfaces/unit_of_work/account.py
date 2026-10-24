"""Граница транзакции аккаунтов."""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from backend.application.interfaces.repositories.account_repository import AccountRepository
from backend.application.interfaces.unit_of_work.transaction import TransactionalUnitOfWork


class AccountUnitOfWork(TransactionalUnitOfWork):
    """Транзакция только по таблице аккаунтов."""

    @property
    @abstractmethod
    def accounts(self) -> AccountRepository:
        """Репозиторий аккаунтов, привязанный к текущей транзакции."""


class AccountUnitOfWorkFactory(Protocol):
    """Создаёт свежую границу транзакции аккаунтов."""

    def __call__(self) -> AccountUnitOfWork:
        """Возвращает новую границу."""
