"""Ports of the hardware the backend drives.

The board transport is addressed by account and, inside an account, by the board
identifier. A user may own several boards, so addressing an account alone would
make the second board kick the first one out.

Inbound reports arrive through a sink that the transport resolves per connection,
so a stream can never reach the home of somebody else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.domain.boards.network_profile import NetworkProfile
from backend.domain.climate.climate_reading import ClimateReading
from backend.domain.identifiers import EspDeviceId, UserId


@dataclass(frozen=True, slots=True)
class BoardCommandResult:
    """What the board answered to a relay command.

    Args:
        accepted: Whether the board confirmed the command.
        reason: Machine readable failure reason, or None on success.

    Returns:
        None.
    """

    accepted: bool
    reason: str | None = None


class BoardGateway(ABC):
    """Drives the relay channels of the boards."""

    @abstractmethod
    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Switch a relay and wait for the confirmation.

        A board that is not connected is reported as a refused result instead of
        an exception, so availability stays a decision of the caller rather than a
        transport error.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            channel: Physical relay channel.
            energized: True to close the contact, False to release it.

        Returns:
            BoardCommandResult: What the board answered.
        """

    @abstractmethod
    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Ask a board to resend everything it knows.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """

    @abstractmethod
    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        """Tell a board which network it is to use.

        The board writes the settings into its own flash and reconnects, so the
        change survives a power cycle. A board that is not connected is reported
        as a refused result instead of an exception, because a board that has
        never been set up cannot receive anything anyway.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            profile: Network the board is to use.

        Returns:
            BoardCommandResult: What the board answered.
        """


class MicrophonePort(ABC):
    """Opens and closes the microphone of a board."""

    @abstractmethod
    async def arm(
        self, user_id: UserId, board_id: EspDeviceId, sample_rate: int, max_sec: int
    ) -> bool:
        """Let a board stream the next phrase.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            sample_rate: Samples per second the board should use.
            max_sec: Longest phrase the board may send.

        Returns:
            bool: True when the request reached the board.
        """

    @abstractmethod
    async def disarm(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Stop a board from streaming audio.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the request reached the board.
        """

    @abstractmethod
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

    @abstractmethod
    async def play(self, user_id: UserId, board_id: EspDeviceId, audio: bytes) -> bool:
        """Play an answer on the speaker of a board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            audio: Rendered audio of the phrase.

        Returns:
            bool: True when the request reached the board.
        """


class BoardReport(ABC):
    """Everything one board reports while it is connected."""

    @abstractmethod
    async def on_connected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Handle a new board connection.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """

    @abstractmethod
    async def on_disconnected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Handle a lost board connection.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """

    @abstractmethod
    async def on_relay_states(
        self, user_id: UserId, board_id: EspDeviceId, states: list[bool]
    ) -> None:
        """Handle reported relay positions.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            states: Contact positions ordered by channel.

        Returns:
            None.
        """

    @abstractmethod
    async def on_reading(
        self, user_id: UserId, board_id: EspDeviceId, reading: ClimateReading
    ) -> None:
        """Handle a sensor report.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            reading: Measured values.

        Returns:
            None.
        """

    @abstractmethod
    async def on_error(
        self, user_id: UserId, board_id: EspDeviceId, code: str, message: str
    ) -> None:
        """Handle an error reported by a board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            code: Machine readable error code.
            message: Human readable error description.

        Returns:
            None.
        """


class MicrophoneStream(ABC):
    """Consumer of the microphone stream of one board."""

    @abstractmethod
    async def on_started(self, user_id: UserId, board_id: EspDeviceId, sample_rate: int) -> None:
        """Handle the beginning of a phrase.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            sample_rate: Samples per second the board streams with.

        Returns:
            None.
        """

    @abstractmethod
    async def on_samples(self, user_id: UserId, board_id: EspDeviceId, data: bytes) -> None:
        """Handle the next piece of a phrase.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            data: Raw signed sixteen bit little endian samples.

        Returns:
            None.
        """

    @abstractmethod
    async def on_stopped(self, user_id: UserId, board_id: EspDeviceId, reason: str) -> None:
        """Handle the end of a phrase.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            reason: Why the board stopped.

        Returns:
            None.
        """
