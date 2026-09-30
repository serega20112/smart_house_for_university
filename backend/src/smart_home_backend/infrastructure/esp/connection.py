"""WebSocket transport between the backend and the board.

The backend listens and the board dials in as a client. This module owns the
socket lifecycle and matches relay commands with their acknowledgements, while
every payload is handed over to the application handler port.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from smart_home_backend.application.interface.services import CommandOutcome, EspStateHandler
from smart_home_backend.infrastructure.esp import protocol
from smart_home_backend.infrastructure.logging_config import get_logger

log = get_logger("esp.connection")

ESP_OFFLINE = "esp_offline"
ACK_TIMEOUT = "ack_timeout"


def _load_serve() -> Callable[..., Any]:
    try:
        from websockets.asyncio.server import serve

        return serve
    except ImportError:
        from websockets.server import serve

        return serve


class EspConnection:
    """Single board connection with command acknowledgements."""

    def __init__(
        self,
        host: str,
        port: int,
        path: str,
        handler_provider: Callable[[], EspStateHandler],
        command_timeout: float = 5.0,
    ) -> None:
        """Initialize the connection.

        Args:
            host: Bind host of the WebSocket server.
            port: Bind port of the WebSocket server.
            path: Path the board connects to.
            handler_provider: Callable returning the inbound data handler.
            command_timeout: How long a command waits for its acknowledgement.

        Returns:
            None.
        """
        self._host = host
        self._port = port
        self._path = path
        self._handler_provider = handler_provider
        self._command_timeout = command_timeout

        self._socket: Any | None = None
        self._server: Any | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._command_counter = 0

    async def start(self) -> None:
        """Start listening for the board.

        Returns:
            None.
        """
        serve = _load_serve()
        self._server = await serve(
            self._serve_client,
            self._host,
            self._port,
            ping_interval=20,
            ping_timeout=10,
        )
        log.info("ESP WebSocket server started", extra={"ctx": {"port": self._port}})

    async def stop(self) -> None:
        """Close the board connection and stop listening.

        Returns:
            None.
        """
        if self._socket is not None:
            await self._socket.close()
            self._socket = None
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def set_relay(self, channel: int, on: bool) -> CommandOutcome:
        """Switch a relay and wait for the acknowledgement.

        Args:
            channel: Physical relay channel.
            on: New relay state.

        Returns:
            CommandOutcome: Result of the command, failed when the board is
            unreachable or does not answer in time.
        """
        if self._socket is None:
            return CommandOutcome(ok=False, error=ESP_OFFLINE)

        self._command_counter += 1
        command_id = f"c{self._command_counter}"
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[command_id] = future
        try:
            await self._socket.send(protocol.build_set_relay(command_id, channel, on))
            await asyncio.wait_for(future, timeout=self._command_timeout)
            return CommandOutcome(ok=True)
        except asyncio.TimeoutError:
            return CommandOutcome(ok=False, error=ACK_TIMEOUT)
        except Exception as exc:
            log.warning("relay command failed", extra={"ctx": {"error": str(exc)}})
            return CommandOutcome(ok=False, error=str(exc))
        finally:
            self._pending.pop(command_id, None)

    async def request_state(self) -> None:
        """Ask the board to resend its full state.

        Returns:
            None.
        """
        if self._socket is not None:
            await self._socket.send(protocol.build_get_state())

    async def _serve_client(self, connection: Any, *_: Any) -> None:
        if not self._matches_path(connection):
            await connection.close(code=4404)
            return
        await self._take_over(connection)

    async def _take_over(self, connection: Any) -> None:
        if self._socket is not None:
            try:
                await self._socket.close()
            except Exception:
                log.info("previous board connection closed")

        self._socket = connection
        handler = self._handler_provider()
        await handler.on_connected()
        try:
            async for raw in connection:
                await self._dispatch(raw, handler)
        except Exception as exc:
            log.warning("board connection failed", extra={"ctx": {"error": str(exc)}})
        finally:
            if self._socket is connection:
                self._socket = None
            await handler.on_disconnected()

    def _matches_path(self, connection: Any) -> bool:
        request = getattr(connection, "request", None)
        path = getattr(request, "path", None) or getattr(connection, "path", "")
        return path in (self._path, f"{self._path}/")

    async def _dispatch(self, raw: str, handler: EspStateHandler) -> None:
        message = protocol.parse(raw)
        if message is None:
            await handler.on_error("BAD_MESSAGE", protocol.UNRECOGNIZED_MESSAGE)
            return
        if message.type == protocol.InboundType.HELLO:
            log.info("board handshake received")
            return
        if message.type == protocol.InboundType.ACK:
            self._resolve_ack(message.command_id)
            return
        if message.type == protocol.InboundType.ERROR:
            await handler.on_error(message.code, message.message)
            return
        if message.type == protocol.InboundType.STATE:
            relays = message.relays
            if relays:
                await handler.on_relay_states(relays)
            await handler.on_reading(message.temperature, message.humidity)
            return
        if message.type == protocol.InboundType.SENSOR_DATA:
            await handler.on_reading(message.temperature, message.humidity)

    def _resolve_ack(self, command_id: str | None) -> None:
        if command_id is None:
            return
        future = self._pending.pop(command_id, None)
        if future is not None and not future.done():
            future.set_result(True)
