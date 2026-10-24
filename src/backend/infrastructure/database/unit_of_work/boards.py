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
    """Транзакция над платами системы.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    @property
    def boards(self) -> BoardRepository:
        """Хранилище сопряжённых плат нынешней транзакции."""
        return self.repository(SqlBoardRepository)

    @property
    def claims(self) -> ClaimRepository:
        """Хранилище объявленных плат нынешней транзакции."""
        return self.repository(SqlClaimRepository)

    @property
    def networks(self) -> BoardNetworkRepository:
        """Хранилище сетей плат нынешней транзакции."""
        return self.repository(SqlBoardNetworkRepository)


def make_board_onboarding_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> BoardOnboardingUnitOfWorkFactory:
    """Строит фабрику границ транзакции над платами.

    Args:
        session_factory: Фабрика сессий.

    Returns:
        BoardOnboardingUnitOfWorkFactory: Вызываемый объект, дающий свежую границу.
    """

    def factory() -> SqlBoardOnboardingUnitOfWork:
        """Создаёт новую границу над платами."""
        return SqlBoardOnboardingUnitOfWork(session_factory)

    return factory
