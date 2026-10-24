"""Среда процесса: часы и пул HTTP-соединений."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide

from backend.application.interfaces.services.system.clock import Clock
from backend.config.settings import Settings
from backend.infrastructure.system.clock import SystemClock

APP = Scope.APP


class RuntimeProvider(Provider):
    """То, что процесс получает от рантайма, а не от внешней системы."""

    @provide(scope=APP)
    def clock(self) -> Clock:
        """Собирает часы, от которых приходит каждая метка времени."""
        return SystemClock()

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
