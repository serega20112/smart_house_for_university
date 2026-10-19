"""Transaction boundary of the board onboarding.

Taking a board over writes both the offer and the board row, and the two have to
land together or nobody owns anything. That is the whole reason this boundary is
separate from the home: it is short, it is about hardware ownership, and it must
not be able to drag a dashboard rewrite into the same transaction.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from backend.application.ports.repositories.boards import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from backend.application.ports.unit_of_work.transaction import TransactionalUnitOfWork


class BoardOnboardingUnitOfWork(TransactionalUnitOfWork):
    """Transaction over the boards of the system."""

    @property
    @abstractmethod
    def boards(self) -> BoardRepository:
        """Return the paired board repository bound to the current transaction.

        Returns:
            BoardRepository: Paired board repository.
        """

    @property
    @abstractmethod
    def claims(self) -> ClaimRepository:
        """Return the announced board repository of the current transaction.

        Returns:
            ClaimRepository: Announced board repository.
        """

    @property
    @abstractmethod
    def networks(self) -> BoardNetworkRepository:
        """Return the network repository bound to the current transaction.

        Returns:
            BoardNetworkRepository: Network repository.
        """


class BoardOnboardingUnitOfWorkFactory(Protocol):
    """Produces a fresh unit of work over the boards."""

    def __call__(self) -> BoardOnboardingUnitOfWork:
        """Create a new unit of work.

        Returns:
            BoardOnboardingUnitOfWork: New unit of work.
        """
