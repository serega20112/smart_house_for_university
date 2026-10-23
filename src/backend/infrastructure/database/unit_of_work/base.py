"""Сессия, транзакция и кеш хранилищ.

Границы транзакций: одна сессия, одна транзакция, свои хранилища.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, cast

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction, async_sessionmaker


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
    ) -> None:
        """End the transaction and release the session.

        The exception, if there was one, keeps propagating after the rollback.

        Args:
            exc_type: Raised exception type or None.
            exc_val: Raised exception value or None.
            exc_tb: Raised exception traceback or None.
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
