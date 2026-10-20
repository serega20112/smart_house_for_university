"""WebSocket hub broadcasting realtime events.

The application publishes events through Redis, so a process that keeps no
sockets still delivers them: every instance of the backend swaps messages through
the broker, and the instance that happens to hold the socket of an account
forwards them to the browser.

Clients are grouped by the account they authenticated as, and an event only ever
reaches the sockets of its own owner, so one user never observes a change in the
home of another one.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict

from fastapi import WebSocket

from smart_home.domain.identifiers import UserId
from smart_home.infrastructure.logging import get_logger
from smart_home.infrastructure.redis.event_broker import RedisSubscriber

log = get_logger("websocket.hub")


class WebSocketHub:
    """Forwards the events of each account to the sockets of that account.

    Args:
        subscriber: Reader of the realtime channels of Redis.

    Returns:
        None.
    """

    def __init__(self, subscriber: RedisSubscriber) -> None:
        """Initialize an empty hub.

        Args:
            subscriber: Reader of the realtime channels of Redis.

        Returns:
            None.
        """
        self._subscriber = subscriber
        self._clients: dict[UserId, set[WebSocket]] = defaultdict(set)
        self._readers: dict[UserId, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UserId, websocket: WebSocket) -> None:
        """Accept a new client connection and make sure events reach it.

        Args:
            user_id: Account the connection was authorized as.
            websocket: Client connection.

        Returns:
            None.
        """
        await websocket.accept()
        async with self._lock:
            self._clients[user_id].add(websocket)
            if user_id not in self._readers:
                self._readers[user_id] = asyncio.create_task(
                    self._pump(user_id), name=f"events-{user_id}"
                )
        log.info(
            "web client connected",
            extra={"ctx": {"user": str(user_id), "clients": self._count()}},
        )

    async def disconnect(self, user_id: UserId, websocket: WebSocket) -> None:
        """Forget a client connection and stop reading for an empty account.

        Args:
            user_id: Account the connection was authorized as.
            websocket: Client connection.

        Returns:
            None.
        """
        async with self._lock:
            self._clients[user_id].discard(websocket)
            if self._clients[user_id]:
                return
            self._clients.pop(user_id, None)
            reader = self._readers.pop(user_id, None)
        if reader is not None:
            reader.cancel()

    async def stop(self) -> None:
        """Stop every reader of this process.

        Returns:
            None.
        """
        async with self._lock:
            readers = list(self._readers.values())
            self._readers.clear()
            self._clients.clear()
        for reader in readers:
            reader.cancel()
        for reader in readers:
            with contextlib.suppress(asyncio.CancelledError):
                await reader

    async def _pump(self, user_id: UserId) -> None:
        """Forward every event of one account to its sockets.

        A socket that fails to receive is dropped; a failure of the whole
        subscription is logged and retried after a pause, because a Redis blip
        must not permanently silence the interface.

        Args:
            user_id: Account the channel belongs to.

        Returns:
            None.
        """
        while True:
            try:
                async for event in self._subscriber.stream(user_id):
                    await self._deliver(user_id, event.event, event.payload)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                log.warning(
                    "websocket.reader_failed",
                    extra={"ctx": {"user": str(user_id), "error": str(error)}},
                )
                await asyncio.sleep(1.0)

    async def _deliver(self, user_id: UserId, event: str, payload: dict) -> None:
        async with self._lock:
            clients = list(self._clients.get(user_id, ()))
        if not clients:
            return
        message = {"type": event, "payload": payload}
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                await self.disconnect(user_id, client)

    def _count(self) -> int:
        return sum(len(clients) for clients in self._clients.values())
