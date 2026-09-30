"""Database engine and session management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from smart_home_backend.infrastructure.database.models import Base


def build_engine(url: str, echo: bool = False) -> AsyncEngine:
    """Create the async engine for the given connection URL.

    Args:
        url: Async SQLAlchemy connection URL.
        echo: Whether SQL statements are logged.

    Returns:
        AsyncEngine: Configured engine.
    """
    return create_async_engine(url, echo=echo, future=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the session factory used by the unit of work.

    Args:
        engine: Engine to bind sessions to.

    Returns:
        async_sessionmaker[AsyncSession]: Session factory.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    """Create the tables that do not exist yet.

    Args:
        engine: Engine owning the schema.

    Returns:
        None.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
