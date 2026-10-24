"""Сессия, транзакция и кеш хранилищ.

Границы транзакций: одна сессия, одна транзакция, свои хранилища.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, cast

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction, async_sessionmaker


class SessionBound(Protocol):
    """Хранилище, принимающее сессию транзакции.

    Attributes:
        session: Сессия, которую открыла граница транзакции.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище сессией текущей транзакции.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """


class SqlUnitOfWork:
    """Одна сессия, одна транзакция и привязанные к ним хранилища.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует границу транзакции.

        Args:
            session_factory: Фабрика сессий.
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._transaction: AsyncSessionTransaction | None = None
        self._repositories: dict[type[SessionBound], SessionBound] = {}

    async def __aenter__(self) -> Self:
        """Открывает сессию и транзакцию блока.

        Returns:
            Self: Граница, годная к употреблению внутри блока.
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
        """Заканчивает транзакцию и отпускает сессию.

        Исключение, если оно было, продолжается после отката.

        Args:
            exc_type: Тип поднятого исключения или None.
            exc_val: Само исключение или None.
            exc_tb: Его traceback или None.
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
        """Атомарно сохраняет всё сделанное внутри блока."""
        if self._transaction is not None:
            await self._transaction.commit()

    async def rollback(self) -> None:
        """Отменяет всё сделанное внутри блока."""
        if self._transaction is not None:
            await self._transaction.rollback()

    @property
    def session(self) -> AsyncSession:
        """Возвращает сессию текущей транзакции.

        Returns:
            AsyncSession: Сессия открытого блока.

        Raises:
            RuntimeError: Когда границу используют вне её блока.
        """
        if self._session is None:
            raise RuntimeError("the unit of work is used outside of its block")
        return self._session

    def repository[Bound: SessionBound](self, model: type[Bound]) -> Bound:
        """Возвращает единственный экземпляр хранилища, который даёт эта граница.

        Кеш нужен, чтобы два вызова внутри одной транзакции видели одни и те же
        объекты, а не два независимых чтения одного состояния.

        Args:
            model: Класс хранилища, который надо вернуть.

        Returns:
            Bound: Хранилище, привязанное к сессии текущей транзакции.

        Raises:
            RuntimeError: Когда границу используют вне её блока.
        """
        if self._session is None:
            raise RuntimeError("the unit of work is used outside of its block")
        cached = self._repositories.get(model)
        if cached is None:
            cached = model(self._session)
            self._repositories[model] = cached
        return cast("Bound", cached)
