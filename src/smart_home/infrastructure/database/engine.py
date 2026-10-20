"""Factories producing the engine and the sessions of the store.

The engine is created once by the composition root and handed to everything that
needs it, so the connection pool is shared instead of being rebuilt per request.
Nothing here opens a session: a session belongs to a unit of work, and the unit
of work is the only component that decides when a transaction ends.

The schema is never created from here. Applying the Alembic revisions is a
deployment step, which keeps the tables of a running system a deliberate decision
rather than a side effect of importing a module.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(
    url: str,
    *,
    echo: bool = False,
    pool_size: int = 10,
    pool_max_overflow: int = 10,
    pool_recycle_sec: int = 1800,
) -> AsyncEngine:
    """Create the async engine for a connection URL.

    Connections are checked before they are handed out and are recycled after the
    configured lifetime, because a board keeps a long lived socket open and the
    database is free to drop a connection nobody has used for a while.

    Args:
        url: Async SQLAlchemy connection URL, using the asyncpg driver.
        echo: Whether every statement is logged.
        pool_size: Number of connections kept open.
        pool_max_overflow: Extra connections allowed when the pool is busy.
        pool_recycle_sec: Age after which a connection is replaced.

    Returns:
        AsyncEngine: Configured engine.
    """
    return create_async_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=pool_max_overflow,
        pool_recycle=pool_recycle_sec,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the session factory the units of work ask for their sessions.

    Objects are not expired when a transaction commits, because the aggregates a
    use case keeps after its block are already plain domain values and a lazy
    refresh would need a session that has been closed.

    Args:
        engine: Engine to bind sessions to.

    Returns:
        async_sessionmaker[AsyncSession]: Session factory.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
