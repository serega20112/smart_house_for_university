"""Units of work binding the session to the repositories.

Three boundaries exist because three lifecycles exist: creating an account, editing
the configuration of a home and taking a board over. Each one opens one session,
one transaction and only the repositories its boundary is allowed to touch, which
is why a dashboard rewrite can never end up in the same transaction as a hardware
takeover.

A unit of work is the only component that commits or rolls back. The repositories
it hands out write into the transaction it opened and never end it themselves.

Every repository is built once per unit of work and then reused, so two property
accesses inside one use case return the same object and both see one consistent
state of the session.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, cast

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction, async_sessionmaker

from smart_home.application.ports.repositories.accounts import AccountRepository
from smart_home.application.ports.repositories.automation import AutomationRepository
from smart_home.application.ports.repositories.boards import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from smart_home.application.ports.repositories.devices import DeviceRepository
from smart_home.application.ports.repositories.personalization import (
    DashboardRepository,
    PreferencesRepository,
)
from smart_home.application.ports.repositories.scenarios import ScenarioRepository
from smart_home.application.ports.unit_of_work.accounts import (
    AccountUnitOfWork,
    AccountUnitOfWorkFactory,
)
from smart_home.application.ports.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWork,
    BoardOnboardingUnitOfWorkFactory,
)
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWork, HomeUnitOfWorkFactory
from smart_home.infrastructure.database.repositories import (
    SqlAccountRepository,
    SqlAutomationRepository,
    SqlBoardNetworkRepository,
    SqlBoardRepository,
    SqlClaimRepository,
    SqlDashboardRepository,
    SqlDeviceRepository,
    SqlPreferencesRepository,
    SqlScenarioRepository,
)


class SessionBound(Protocol):
    """A repository that takes the session of a transaction.

    Args:
        session: Session the unit of work opened.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with the session of the transaction.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """


class SqlUnitOfWork:
    """One session, one transaction, and the repositories bound to them.

    Args:
        session_factory: Factory producing the session of the block.

    Returns:
        None.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize the unit of work.

        Args:
            session_factory: Factory producing sessions.

        Returns:
            None.
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._transaction: AsyncSessionTransaction | None = None
        self._repositories: dict[type[SessionBound], SessionBound] = {}

    async def __aenter__(self) -> Self:
        """Open the session and the transaction of the block.

        Returns:
            Self: Unit of work for use inside the block.
        """
        self._session = self._session_factory()
        self._transaction = await self._session.begin()
        self._repositories.clear()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """End the transaction and release the session.

        Args:
            exc_type: Raised exception type or None.
            exc_val: Raised exception value or None.
            exc_tb: Raised exception traceback or None.

        Returns:
            bool: False so exceptions keep propagating.
        """
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None
            self._transaction = None
            self._repositories.clear()
        return False

    async def commit(self) -> None:
        """Persist everything done inside the block atomically.

        Returns:
            None.
        """
        if self._transaction is not None:
            await self._transaction.commit()

    async def rollback(self) -> None:
        """Discard everything done inside the block.

        Returns:
            None.
        """
        if self._transaction is not None:
            await self._transaction.rollback()

    @property
    def session(self) -> AsyncSession:
        """Return the session of the current transaction.

        Returns:
            AsyncSession: Session of the open block.

        Raises:
            RuntimeError: When the unit of work is used outside its block.
        """
        if self._session is None:
            raise RuntimeError("the unit of work is used outside of its block")
        return self._session

    def repository[Bound: SessionBound](self, model: type[Bound]) -> Bound:
        """Return the one instance of a repository this unit of work hands out.

        Args:
            model: Repository class to return.

        Returns:
            Bound: Repository bound to the session of the current transaction.

        Raises:
            RuntimeError: When the unit of work is used outside its block.
        """
        if self._session is None:
            raise RuntimeError("the unit of work is used outside of its block")
        cached = self._repositories.get(model)
        if cached is None:
            cached = model(self._session)
            self._repositories[model] = cached
        return cast("Bound", cached)


class SqlAccountUnitOfWork(SqlUnitOfWork, AccountUnitOfWork):
    """Transaction over the accounts, and over nothing else.

    Args:
        session_factory: Factory producing the session of the block.

    Returns:
        None.
    """

    @property
    def accounts(self) -> AccountRepository:
        """Return the account repository bound to the current transaction.

        Returns:
            AccountRepository: Account repository.
        """
        return self.repository(SqlAccountRepository)


class SqlHomeUnitOfWork(SqlUnitOfWork, HomeUnitOfWork):
    """Transaction over the configuration of one home.

    Args:
        session_factory: Factory producing the session of the block.

    Returns:
        None.
    """

    @property
    def devices(self) -> DeviceRepository:
        """Return the device repository bound to the current transaction.

        Returns:
            DeviceRepository: Device repository.
        """
        return self.repository(SqlDeviceRepository)

    @property
    def automation(self) -> AutomationRepository:
        """Return the automation repository bound to the current transaction.

        Returns:
            AutomationRepository: Automation repository.
        """
        return self.repository(SqlAutomationRepository)

    @property
    def scenarios(self) -> ScenarioRepository:
        """Return the scenario repository bound to the current transaction.

        Returns:
            ScenarioRepository: Scenario repository.
        """
        return self.repository(SqlScenarioRepository)

    @property
    def dashboard(self) -> DashboardRepository:
        """Return the dashboard repository bound to the current transaction.

        Returns:
            DashboardRepository: Dashboard repository.
        """
        return self.repository(SqlDashboardRepository)

    @property
    def preferences(self) -> PreferencesRepository:
        """Return the preferences repository bound to the current transaction.

        Returns:
            PreferencesRepository: Preferences repository.
        """
        return self.repository(SqlPreferencesRepository)


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


def make_account_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> AccountUnitOfWorkFactory:
    """Build the factory producing units of work over the accounts.

    Args:
        session_factory: Factory producing sessions.

    Returns:
        AccountUnitOfWorkFactory: Callable handing out a fresh unit of work.
    """

    def factory() -> SqlAccountUnitOfWork:
        """Create a new unit of work over the accounts.

        Returns:
            SqlAccountUnitOfWork: Unit of work bound to its own session.
        """
        return SqlAccountUnitOfWork(session_factory)

    return factory


def make_home_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> HomeUnitOfWorkFactory:
    """Build the factory producing units of work over a home.

    Args:
        session_factory: Factory producing sessions.

    Returns:
        HomeUnitOfWorkFactory: Callable handing out a fresh unit of work.
    """

    def factory() -> SqlHomeUnitOfWork:
        """Create a new unit of work over the configuration of a home.

        Returns:
            SqlHomeUnitOfWork: Unit of work bound to its own session.
        """
        return SqlHomeUnitOfWork(session_factory)

    return factory


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
