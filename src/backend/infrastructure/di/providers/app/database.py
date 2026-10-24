"""База процесса: движок и фабрика сессий.

Движок у процесса один, поэтому он живёт в области приложения и переживает всякий
запрос; сессии из его фабрики короткими делают границы транзакции.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from backend.config.settings import Settings
from backend.infrastructure.database.engine import build_engine, build_session_factory

APP = Scope.APP


class DatabaseProvider(Provider):
    """Долгоживущие соединения реляционного хранилища."""

    @provide(scope=APP)
    async def engine(self, settings: Settings) -> AsyncIterator[AsyncEngine]:
        """Собирает движок, который у процесса один."""
        engine = build_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            pool_max_overflow=settings.database_pool_max_overflow,
            pool_recycle_sec=settings.database_pool_recycle_sec,
        )
        yield engine
        await engine.dispose()

    @provide(scope=APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker:
        """Собирает фабрику, у которой единицы работы просят сессии."""
        return build_session_factory(engine)
