"""WebSocket transport between the backend and the boards.

The backend listens and every board dials in as a client, so a board placed in
any home network reaches a backend running on a remote server without a single
incoming connection.

Sessions are keyed by account *and* board. A user may own several boards, and
addressing an account alone would let the second board kick the first one out,
which is exactly what makes a home with more than one room impossible.

Everything the connection needs from the outside is injected: the sink reports
come to, the sink audio arrives at, and the gateway that answers the questions a
handshake raises. Nothing is bound after construction, so a connection is fully
described by its arguments.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Final

from websockets.asyncio.server import Server, ServerConnection, serve

from smart_home.application.ports.boards import BoardReport, MicrophoneStream
from smart_home.domain.boards.network_profile import NetworkProfile
from smart_home.domain.climate.climate_reading import ClimateReading
from smart_home.domain.identifiers import EspDeviceId, UserId
from smart_home.infrastructure.esp import protocol
from smart_home.infrastructure.esp.onboarding import (
    BoardAnnouncement,
    BoardIdentity,
    BoardOnboardingGateway,
)
from smart_home.infrastructure.logging import get_logger

log = get_logger("esp.connection")

BOARD_WEBSOCKET_PATH: Final = "/ws/board"

HANDSHAKE_TIMEOUT_SEC = 10.0
PING_INTERVAL_SEC = 30
PING_TIMEOUT_SEC = 45
CLOSE_WRONG_PATH = 4404
CLOSE_UNKNOWN_KEY = 4401
CLOSE_AWAITING_OWNER = 4403

OFFLINE_REASON: Final = "esp_offline"
ACK_TIMEOUT_REASON: Final = "ack_timeout"
DELIVERY_FAILED_REASON: Final = "esp_delivery_failed"

MicrophoneStreamResolver = Callable[[], Awaitable[MicrophoneStream]]


class MicrophoneStreamForwarder(MicrophoneStream):
    """Microphone sink that resolves the real stream on first use.

    The voice pipeline needs the microphone port, which is a facade over this very
    connection, so the two cannot be handed to each other while the graph is
    built. The composition root injects a forwardable callable that resolves the
    stream from the container; this object is the documented seam, and it exists
    instead of a ``bind_*`` call because the alternative is a half built object
    whose behaviour depends on the order somebody happened to wire it in.

    Args:
        resolve: Callable returning the stream the audio is handed to.

    Returns:
        None.
    """

    def __init__(self, resolve: MicrophoneStreamResolver) -> None:
        """Initialize the forwarder.

        Args:
            resolve: Callable returning the stream the audio is handed to.

        Returns:
            None.
        """
        self._resolve = resolve
        self._stream: MicrophoneStream | None = None

    async def on_started(self, user_id: UserId, board_id: EspDeviceId, sample_rate: int) -> None:
        """Handle the beginning of a phrase.

        Args:
            user_id: Owner of the board that is streaming.
            board_id: Identifier of the board.
            sample_rate: Samples per second the board streams with.

        Returns:
            None.
        """
        await (await self._target()).on_started(user_id, board_id, sample_rate)

    async def on_samples(self, user_id: UserId, board_id: EspDeviceId, data: bytes) -> None:
        """Handle the next piece of a phrase.

        Args:
            user_id: Owner of the board that is streaming.
            board_id: Identifier of the board.
            data: Raw signed sixteen bit little endian samples.

        Returns:
            None.
        """
        await (await self._target()).on_samples(user_id, board_id, data)

    async def on_stopped(self, user_id: UserId, board_id: EspDeviceId, reason: str) -> None:
        """Handle the end of a phrase.

        Args:
            user_id: Owner of the board that was streaming.
            board_id: Identifier of the board.
            reason: Why the board stopped.

        Returns:
            None.
        """
        await (await self._target()).on_stopped(user_id, board_id, reason)

    def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Return whether a board is connected behind the resolved stream.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the board is connected right now.
        """
        stream = self._stream
        if stream is None:
            return False
        return stream.is_connected(user_id, board_id)

    async def _target(self) -> MicrophoneStream:
        if self._stream is None:
            self._stream = await self._resolve()
        return self._stream


class BoardSession:
    """One connected board and the commands waiting for its acknowledgement.

    Args:
        user_id: Owner of the board.
        board_id: Identifier of the board.
        socket: Open WebSocket of the board.
        counter: Source of the identifiers unique inside this session.

    Returns:
        None.
    """

    def __init__(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        socket: ServerConnection,
        counter: Callable[[], str],
    ) -> None:
        """Initialize the session.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            socket: Open WebSocket of the board.
            counter: Source of the identifiers unique inside this session.

        Returns:
            None.
        """
        self.user_id = user_id
        self.board_id = board_id
        self.socket = socket
        self.pending: dict[str, asyncio.Future[None]] = {}
        self._counter = counter

    def next_command_id(self) -> str:
        """Return an identifier unique inside this session.

        Returns:
            str: Identifier used to match an acknowledgement.
        """
        return self._counter()


class EspConnection:
    """Board connections keyed by account and board.

    Args:
        report: Sink the inbound reports of every board are handed to.
        microphone: Sink the audio of every board is handed to.
        onboarding: Gateway answering the questions a handshake raises.
        host: Bind host of the WebSocket server.
        port: Bind port of the WebSocket server.
        path: Path the boards connect to.
        command_timeout_sec: How long a command waits for its acknowledgement.

    Returns:
        None.
    """

    def __init__(
        self,
        report: BoardReport,
        microphone: MicrophoneStream,
        onboarding: BoardOnboardingGateway,
        host: str = "0.0.0.0",
        port: int = 8765,
        path: str = BOARD_WEBSOCKET_PATH,
        command_timeout_sec: float = 5.0,
    ) -> None:
        """Initialize the connection.

        Args:
            report: Sink the inbound reports of every board are handed to.
            microphone: Sink the audio of every board is handed to.
            onboarding: Gateway answering the questions a handshake raises.
            host: Bind host of the WebSocket server.
            port: Bind port of the WebSocket server.
            path: Path the boards connect to.
            command_timeout_sec: How long a command waits for its acknowledgement.

        Returns:
            None.
        """
        self._report = report
        self._microphone = microphone
        self._onboarding = onboarding
        self._host = host
        self._port = port
        self._path = path
        self._command_timeout = command_timeout_sec
        self._sessions: dict[tuple[UserId, EspDeviceId], BoardSession] = {}
        self._counter = 0
        self._server: Server | None = None

    async def start(self) -> None:
        """Start listening for the boards.

        Returns:
            None.
        """
        self._server = await serve(
            self._serve_client,
            self._host,
            self._port,
            ping_interval=PING_INTERVAL_SEC,
            ping_timeout=PING_TIMEOUT_SEC,
        )
        log.info(
            "esp.server_started",
            host=self._host,
            port=self._port,
            path=self._path,
        )

    async def stop(self) -> None:
        """Close every board connection and stop listening.

        Returns:
            None.
        """
        for session in list(self._sessions.values()):
            with suppress(Exception):
                await session.socket.close()
        self._sessions.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        log.info("esp.server_stopped")

    def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Return whether one board of a user is currently connected.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when a session exists for that board.
        """
        return (user_id, board_id) in self._sessions

    def is_account_online(self, user_id: UserId) -> bool:
        """Return whether any board of an account is currently connected.

        Args:
            user_id: Owner the boards belong to.

        Returns:
            bool: True when at least one board is connected.
        """
        return any(owner == user_id for owner, _ in self._sessions)

    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> tuple[bool, str | None]:
        """Switch a relay and wait for the acknowledgement.

        A board that is not connected is reported as a refusal instead of an
        exception, so availability stays a decision of the caller.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            channel: Physical relay channel.
            energized: True to close the contact, False to release it.

        Returns:
            tuple[bool, str | None]: Whether the board confirmed, and the machine
            readable reason when it did not.
        """
        session = self._sessions.get((user_id, board_id))
        if session is None:
            return False, OFFLINE_REASON
        command_id = session.next_command_id()
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        session.pending[command_id] = future
        frame = protocol.SetRelayFrame(command_id=command_id, channel=channel, state=energized)
        try:
            await session.socket.send(frame.to_json())
            await asyncio.wait_for(future, timeout=self._command_timeout)
        except TimeoutError:
            return False, ACK_TIMEOUT_REASON
        except Exception as error:
            log.warning(
                "esp.relay_command_failed",
                user=str(user_id),
                board=str(board_id),
                error=str(error),
            )
            return False, DELIVERY_FAILED_REASON
        finally:
            session.pending.pop(command_id, None)
        return True, None

    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Ask a board to resend everything it knows.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        await self._send(user_id, board_id, protocol.GetStateFrame())

    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> tuple[bool, str | None]:
        """Tell a board which network it is to use and wait for the confirmation.

        The board writes the settings into its own flash before it answers, so a
        confirmed change survives a power cycle even if the board loses the
        connection right after it.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            profile: Network the board is to use.

        Returns:
            tuple[bool, str | None]: Whether the board confirmed, and the machine
            readable reason when it did not.
        """
        session = self._sessions.get((user_id, board_id))
        if session is None:
            return False, OFFLINE_REASON
        command_id = session.next_command_id()
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        session.pending[command_id] = future
        frame = protocol.SetNetworkFrame(
            command_id=command_id,
            ssid=profile.ssid,
            password=profile.password,
            host=profile.host,
            server_port=profile.server_port,
            socket_port=profile.socket_port,
            socket_path=profile.socket_path,
        )
        try:
            await session.socket.send(frame.to_json())
            await asyncio.wait_for(future, timeout=self._command_timeout)
        except TimeoutError:
            return False, ACK_TIMEOUT_REASON
        except Exception as error:
            log.warning(
                "esp.network_command_failed",
                user=str(user_id),
                board=str(board_id),
                error=str(error),
            )
            return False, DELIVERY_FAILED_REASON
        finally:
            session.pending.pop(command_id, None)
        return True, None

    async def arm_microphone(
        self, user_id: UserId, board_id: EspDeviceId, sample_rate: int, max_sec: int
    ) -> bool:
        """Open the recording window of one board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            sample_rate: Samples per second the board should use.
            max_sec: Longest phrase the board may send.

        Returns:
            bool: True when the request reached the board.
        """
        return await self._send(
            user_id, board_id, protocol.ArmMicFrame(sample_rate=sample_rate, max_ms=max_sec * 1000)
        )

    async def disarm_microphone(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Close the recording window of one board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the request reached the board.
        """
        return await self._send(user_id, board_id, protocol.DisarmMicFrame())

    async def set_speech_threshold(
        self, user_id: UserId, board_id: EspDeviceId, threshold: int
    ) -> bool:
        """Change the loudness above which a board sees speech.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            threshold: Threshold within the ten bit range of the board converter.

        Returns:
            bool: True when the request reached the board.
        """
        return await self._send(user_id, board_id, protocol.SetVadFrame(threshold=threshold))

    async def play_audio(self, user_id: UserId, board_id: EspDeviceId, audio: bytes) -> bool:
        """Play an answer on the speaker of one board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            audio: Rendered audio of the phrase.

        Returns:
            bool: True when the audio reached the board.
        """
        session = self._sessions.get((user_id, board_id))
        if session is None:
            return False
        try:
            await session.socket.send(audio)
        except Exception as error:
            log.warning(
                "esp.audio_delivery_failed",
                user=str(user_id),
                board=str(board_id),
                error=str(error),
            )
            return False
        return True

    async def confirm_ownership(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Tell a board that it belongs to an account.

        A board that was just taken dials in again a little later, long after the
        takeover itself, so the confirmation has to travel with the handshake.

        Args:
            user_id: Owner resolved from the key the board presented.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        await self._send(user_id, board_id, protocol.ClaimedFrame())

    async def _send(
        self, user_id: UserId, board_id: EspDeviceId, frame: protocol.OutboundFrame
    ) -> bool:
        session = self._sessions.get((user_id, board_id))
        if session is None:
            return False
        try:
            await session.socket.send(frame.to_json())
        except Exception as error:
            log.warning(
                "esp.frame_delivery_failed",
                user=str(user_id),
                board=str(board_id),
                error=str(error),
            )
            return False
        return True

    async def _serve_client(self, connection: ServerConnection) -> None:
        if not _matches_path(connection, self._path):
            await connection.close(code=CLOSE_WRONG_PATH, reason="unknown path")
            return
        raw = await self._read_handshake(connection)
        if raw is None:
            return
        try:
            frame = protocol.parse_inbound(raw)
        except protocol.MalformedFrameError as error:
            log.warning("esp.handshake_malformed", error=str(error))
            await connection.close(code=CLOSE_UNKNOWN_KEY, reason="malformed handshake")
            return
        identity = await self._authenticate(frame)
        if isinstance(identity, BoardAnnouncement):
            await self._offer_claim(connection, identity)
            return
        if identity is None:
            await connection.close(code=CLOSE_UNKNOWN_KEY, reason="unknown pairing key")
            return
        await self._pump(connection, identity)

    async def _read_handshake(self, connection: ServerConnection) -> str | None:
        try:
            raw = await asyncio.wait_for(connection.recv(), timeout=HANDSHAKE_TIMEOUT_SEC)
        except TimeoutError:
            log.warning("esp.handshake_timeout")
            await connection.close(code=CLOSE_UNKNOWN_KEY, reason="handshake timeout")
            return None
        except Exception as error:
            log.warning("esp.handshake_failed", error=str(error))
            return None
        if isinstance(raw, bytes | bytearray):
            log.warning(
                "esp.handshake_binary",
                size=len(raw),
                head=bytes(raw[:60]).decode("utf-8", "replace"),
            )
            return None
        return raw

    async def _authenticate(
        self, frame: protocol.InboundFrame
    ) -> BoardIdentity | BoardAnnouncement | None:
        if not isinstance(frame, protocol.HelloFrame) or not frame.pairing_key:
            log.warning("esp.handshake_without_key")
            return None
        identity = await self._onboarding.resolve_pairing_key(frame.pairing_key)
        if identity is not None:
            await self._onboarding.record_last_seen(identity.board_id, frame.ssid)
            return identity
        offered = await self._onboarding.announce(frame.pairing_key, frame.label)
        if offered is None:
            log.warning("esp.board_not_announced", label=frame.label)
        return offered

    async def _offer_claim(self, connection: ServerConnection, offered: BoardAnnouncement) -> None:
        """Tell a board that it is known and waiting to be taken.

        The connection is closed on purpose: the board is not paired with anybody,
        so it must not receive a single command. It dials in again on its own, and
        by then the account that took it is already stored.

        Args:
            connection: Connection of the unpaired board.
            offered: Offer published for that board.

        Returns:
            None.
        """
        frame = protocol.ClaimFrame(label=offered.label, ttl_sec=offered.ttl_sec)
        with suppress(Exception):
            await connection.send(frame.to_json())
        await connection.close(code=CLOSE_AWAITING_OWNER, reason="awaiting owner")
        log.info("esp.board_announced", label=offered.label, ttl_sec=offered.ttl_sec)

    async def _pump(self, connection: ServerConnection, identity: BoardIdentity) -> None:
        key = (identity.user_id, identity.board_id)
        self._counter += 1
        counter = _counter_factory(identity.board_id, self._counter)
        session = BoardSession(identity.user_id, identity.board_id, connection, counter)
        self._sessions[key] = session
        await self._report.on_connected(identity.user_id, identity.board_id)
        await self.confirm_ownership(identity.user_id, identity.board_id)
        await self.request_state(identity.user_id, identity.board_id)
        log.info(
            "esp.board_connected",
            user=str(identity.user_id),
            board=str(identity.board_id),
        )
        try:
            async for raw in connection:
                if isinstance(raw, bytes | bytearray):
                    await self._on_samples(session, bytes(raw))
                else:
                    await self._on_frame(session, raw)
        except Exception as error:
            log.warning(
                "esp.board_connection_failed",
                user=str(identity.user_id),
                board=str(identity.board_id),
                error=str(error),
            )
        finally:
            if self._sessions.get(key) is session:
                self._sessions.pop(key, None)
            for future in session.pending.values():
                if not future.done():
                    future.cancel()
            await self._report.on_disconnected(identity.user_id, identity.board_id)
            log.info(
                "esp.board_disconnected",
                user=str(identity.user_id),
                board=str(identity.board_id),
            )

    async def _on_samples(self, session: BoardSession, samples: bytes) -> None:
        await self._microphone.on_samples(session.user_id, session.board_id, samples)

    async def _on_frame(self, session: BoardSession, raw: str) -> None:
        try:
            frame = protocol.parse_inbound(raw)
        except protocol.MalformedFrameError as error:
            log.warning(
                "esp.frame_malformed",
                user=str(session.user_id),
                board=str(session.board_id),
                error=str(error),
            )
            await self._report.on_error(
                session.user_id, session.board_id, "BAD_MESSAGE", str(error)
            )
            return
        await self._dispatch(session, frame)

    async def _dispatch(self, session: BoardSession, frame: protocol.InboundFrame) -> None:
        user_id, board_id = session.user_id, session.board_id
        if isinstance(frame, protocol.HelloFrame):
            log.info(
                "esp.board_hello",
                user=str(user_id),
                board=str(board_id),
                mic=frame.mic,
                firmware=frame.firmware,
            )
        elif isinstance(frame, protocol.AckFrame):
            _resolve_ack(session, frame.command_id)
        elif isinstance(frame, protocol.ErrorFrame | protocol.MicErrorFrame):
            await self._report.on_error(user_id, board_id, frame.code, frame.message)
        elif isinstance(frame, protocol.MicLevelFrame):
            _log_level(session, frame)
        elif isinstance(frame, protocol.AudioStartFrame):
            await self._microphone.on_started(user_id, board_id, frame.sample_rate)
        elif isinstance(frame, protocol.AudioStopFrame):
            await self._microphone.on_stopped(user_id, board_id, frame.reason)
        elif isinstance(frame, protocol.StateFrame):
            if frame.relays:
                await self._report.on_relay_states(user_id, board_id, list(frame.relays))
            await self._report.on_reading(
                user_id, board_id, ClimateReading.measured(frame.temperature, frame.humidity)
            )
        elif isinstance(frame, protocol.SensorDataFrame):
            await self._report.on_reading(
                user_id, board_id, ClimateReading.measured(frame.temperature, frame.humidity)
            )


def _counter_factory(board_id: EspDeviceId, start: int) -> Callable[[], str]:
    counter = start

    def next_id() -> str:
        """Return an identifier unique inside the session.

        Returns:
            str: Identifier used to match an acknowledgement.
        """
        nonlocal counter
        counter += 1
        return f"{str(board_id)[:8]}-{counter}"

    return next_id


def _resolve_ack(session: BoardSession, command_id: str) -> None:
    future = session.pending.pop(command_id, None)
    if future is not None and not future.done():
        future.set_result(None)


def _log_level(session: BoardSession, frame: protocol.MicLevelFrame) -> None:
    """Write down how loud the microphone of a board is.

    This is the only way to tell a quiet room from a broken microphone, and it is
    what the speech threshold is tuned against.

    Args:
        session: Board that reported the level.
        frame: Frame carrying the measurement.

    Returns:
        None.
    """
    log.info(
        "esp.microphone_level",
        user=str(session.user_id),
        board=str(session.board_id),
        rms=frame.rms,
        threshold=frame.threshold,
        speech=bool(frame.threshold) and frame.rms >= frame.threshold,
    )


def _matches_path(connection: ServerConnection, path: str) -> bool:
    request = getattr(connection, "request", None)
    actual = getattr(request, "path", None) or getattr(connection, "path", "")
    return actual in (path, f"{path}/")
