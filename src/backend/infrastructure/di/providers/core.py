"""Ядро: часы, движок базы, фабрика сессий, Redis и HTTP-соединение."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from backend.application.interface.services.clock import Clock
from backend.config.settings import Settings
from backend.infrastructure.clock import SystemClock
from backend.infrastructure.database.engine import build_engine, build_session_factory

APP = Scope.APP


class CoreProvider(Provider):
    """Настройки, часы и долгоживущие клиенты процесса."""

    @provide(scope=APP)
    def clock(self) -> Clock:
        """Собирает часы, от которых приходит каждая метка времени."""
        return SystemClock()

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

    @provide(scope=APP)
    async def redis(self, settings: Settings) -> AsyncIterator[Redis]:
        """Собирает соединение, в котором лежит всё недолгое."""
        client: Redis = Redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
        )
        yield client
        await client.aclose()

    @provide(scope=APP)
    async def http_client(self, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
        """Собирает пул соединений к машине, на которой живут модели."""
        client = httpx.AsyncClient(
            timeout=settings.language_timeout_sec,
            limits=httpx.Limits(
                max_connections=settings.http_max_connections,
                max_keepalive_connections=settings.http_max_keepalive_connections,
            ),
        )
        yield client
        await client.aclose()
