"""SQLAlchemy implementation of the unit of work."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from smart_home_backend.application.interface.unit_of_work import UnitOfWork
from smart_home_backend.infrastructure.database.automation_repository import (
    SqlAutomationRepository,
)
from smart_home_backend.infrastructure.database.device_repository import SqlDeviceRepository
from smart_home_backend.infrastructure.database.scenario_repository import (
    SqlScenarioRepository,
)


class SqlUnitOfWork(UnitOfWork):
    """Owns one session and the repositories bound to it."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize the unit of work.

        Args:
            session_factory: Factory producing sessions.

        Returns:
            None.
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def _active_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork is used outside of its context manager")
        return self._session

    @property
    def devices(self) -> SqlDeviceRepository:
        """Return the device repository of the current transaction.

        Returns:
            SqlDeviceRepository: Device repository.
        """
        return SqlDeviceRepository(self._active_session)

    @property
    def automation(self) -> SqlAutomationRepository:
        """Return the automation repository of the current transaction.

        Returns:
            SqlAutomationRepository: Automation repository.
        """
        return SqlAutomationRepository(self._active_session)

    @property
    def scenarios(self) -> SqlScenarioRepository:
        """Return the scenario repository of the current transaction.

        Returns:
            SqlScenarioRepository: Scenario repository.
        """
        return SqlScenarioRepository(self._active_session)

    async def commit(self) -> None:
        """Persist all pending changes atomically.

        Returns:
            None.
        """
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        """Discard all pending changes.

        Returns:
            None.
        """
        if self._session is not None:
            await self._session.rollback()

    async def __aenter__(self) -> "SqlUnitOfWork":
        """Open a session for the transaction.

        Returns:
            SqlUnitOfWork: Self for use inside the with block.
        """
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Commit or roll back and release the session.

        Args:
            exc_type: Raised exception type or None.
            exc_val: Raised exception value or None.
            exc_tb: Raised exception traceback or None.

        Returns:
            bool: False so exceptions propagate.
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
        return False
