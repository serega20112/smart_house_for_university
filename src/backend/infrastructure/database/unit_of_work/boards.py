"""Транзакция сопряжения платы.

Границы транзакций: одна сессия, одна транзакция, свои хранилища.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.interface.repositories.board_repository import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from backend.application.interface.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWork,
    BoardOnboardingUnitOfWorkFactory,
)
from backend.infrastructure.database.repositories import (
    SqlBoardNetworkRepository,
    SqlBoardRepository,
    SqlClaimRepository,
)
from backend.infrastructure.database.unit_of_work.base import SqlUnitOfWork


class SqlBoardOnboardingUnitOfWork(SqlUnitOfWork, BoardOnboardingUnitOfWork):
    """Transaction over the boards of the system.

    Args:
        session_factory: Factory producing the session of the block.

    Returns:
        None.
    """

    @property
    def boards(self) -> BoardRepository:
        """Return the paired board repository bound to the current transaction.

        Returns:
            BoardRepository: Paired board repository.
        """
        return self.repository(SqlBoardRepository)

    @property
    def claims(self) -> ClaimRepository:
        """Return the announced board repository of the current transaction.

        Returns:
            ClaimRepository: Announced board repository.
        """
        return self.repository(SqlClaimRepository)

    @property
    def networks(self) -> BoardNetworkRepository:
        """Return the network repository of the current transaction.

        Returns:
            BoardNetworkRepository: Network repository.
        """
        return self.repository(SqlBoardNetworkRepository)


def make_board_onboarding_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> BoardOnboardingUnitOfWorkFactory:
    """Build the factory producing units of work over the boards.

    Args:
        session_factory: Factory producing sessions.

    Returns:
        BoardOnboardingUnitOfWorkFactory: Callable handing out a fresh unit of
        work.
    """

    def factory() -> SqlBoardOnboardingUnitOfWork:
        """Create a new unit of work over the boards.

        Returns:
            SqlBoardOnboardingUnitOfWork: Unit of work bound to its own session.
        """
        return SqlBoardOnboardingUnitOfWork(session_factory)

    return factory
