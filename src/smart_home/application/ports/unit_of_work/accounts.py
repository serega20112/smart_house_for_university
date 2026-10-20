"""Transaction boundary of the accounts."""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from smart_home.application.ports.repositories.accounts import AccountRepository
from smart_home.application.ports.unit_of_work.transaction import TransactionalUnitOfWork


class AccountUnitOfWork(TransactionalUnitOfWork):
    """Transaction over the account table only."""

    @property
    @abstractmethod
    def accounts(self) -> AccountRepository:
        """Return the account repository bound to the current transaction.

        Returns:
            AccountRepository: Account repository.
        """


class AccountUnitOfWorkFactory(Protocol):
    """Produces a fresh unit of work over the accounts."""

    def __call__(self) -> AccountUnitOfWork:
        """Create a new unit of work.

        Returns:
            AccountUnitOfWork: New unit of work.
        """
