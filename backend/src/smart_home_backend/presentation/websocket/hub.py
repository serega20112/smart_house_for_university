"""WebSocket hub broadcasting realtime events.

Implements the event bus port: the application publishes domain events without
knowing about WebSockets. A broken client connection never fails the business
operation that produced the event.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.infrastructure.logging_config import get_logger

log = get_logger("websocket.hub")


class WebSocketHub(EventBus):
    """Broadcasts events to every connected web client."""

    def __init__(self) -> None:
        """Initialize an empty hub.

        Returns:
            None.
        """
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new client connection.

        Args:
            websocket: Client connection.

        Returns:
            None.
        """
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        log.info("web client connected", extra={"ctx": {"clients": len(self._clients)}})

    async def disconnect(self, websocket: WebSocket) -> None:
        """Forget a client connection.

        Args:
            websocket: Client connection.

        Returns:
            None.
        """
        async with self._lock:
            self._clients.discard(websocket)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send an event to every client and drop the dead ones.

        Args:
            event_type: Event name.
            payload: JSON serializable event data.

        Returns:
            None.
        """
        message = {"type": event_type, "payload": payload}
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)
