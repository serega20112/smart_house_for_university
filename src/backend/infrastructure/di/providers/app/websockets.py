"""Концентратор соединений интерфейса: живёт вместе с процессом и гасится вместе с ним."""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from backend.infrastructure.brokers.event_broker import RedisSubscriber
from backend.infrastructure.websockets.hub import WebSocketHub

APP = Scope.APP


class WebSocketsProvider(Provider):
    """Раздача событий тем сокетам, которые этот процесс держит."""

    @provide(scope=APP)
    async def hub(self, subscriber: RedisSubscriber) -> AsyncIterator[WebSocketHub]:
        """Собирает концентратор и останавливает его читателей на закрытии процесса.

        Args:
            subscriber: Читатель каналов событий Redis.

        Yields:
            WebSocketHub: Концентратор этого процесса.
        """
        hub = WebSocketHub(subscriber)
        yield hub
        await hub.stop()
