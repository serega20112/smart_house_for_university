"""WebSocket hub broadcasting realtime events.

Implements the event bus port: the application publishes domain events without
knowing about WebSockets. A broken client connection never fails the business
operation that produced the event.

Clients are grouped by the account they authenticated as, and an event only ever
reaches the sockets of its own owner, so one user never observes a change in the
home of another one.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from backend.application.interface.services import EventBus
from backend.domain.value_objects.identity import UserId
from backend.infrastructure.logging_config import get_logger

log = get_logger("websocket.hub")


class WebSocketHub(EventBus):
    """Broadcasts events to the clients of the user they belong to."""

    def __init__(self) -> None:
        """Initialize an empty hub.

        Returns:
            None.
        """
        self._clients: dict[UserId, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UserId, websocket: WebSocket) -> None:
        """Accept a new client connection.

        Args:
            user_id: Account the connection was authorized as.
            websocket: Client connection.

        Returns:
            None.
        """
        await websocket.accept()
        async with self._lock:
            self._clients[user_id].add(websocket)
        log.info(
            "web client connected",
            extra={"ctx": {"user": str(user_id), "clients": self._count()}},
        )

    async def disconnect(self, user_id: UserId, websocket: WebSocket) -> None:
        """Forget a client connection.

        Args:
            user_id: Account the connection was authorized as.
            websocket: Client connection.

        Returns:
            None.
        """
        async with self._lock:
            self._clients[user_id].discard(websocket)
            if not self._clients[user_id]:
                self._clients.pop(user_id, None)

    async def publish(self, user_id: UserId, event_type: str, payload: dict[str, Any]) -> None:
        """Send an event to the clients of one user and drop the dead ones.

        Args:
            user_id: Owner the event belongs to.
            event_type: Event name.
            payload: JSON serializable event data.

        Returns:
            None.
        """
        async with self._lock:
            clients = list(self._clients.get(user_id, ()))
        if not clients:
            return
        message = {"type": event_type, "payload": payload}
        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients[user_id].discard(client)

    def _count(self) -> int:
        return sum(len(clients) for clients in self._clients.values())
