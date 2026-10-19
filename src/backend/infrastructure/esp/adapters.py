"""The two faces of the board transport.

:class:`BoardGatewayAdapter` and :class:`EspMicrophoneAdapter` are two thin
facades over one WebSocket connection, which is the reason they live in a single
module: splitting them would scatter the description of the transport across
files that each carry no logic of their own.
"""

from __future__ import annotations

from backend.application.ports.boards import BoardCommandResult, BoardGateway, MicrophonePort
from backend.domain.boards.network_profile import NetworkProfile
from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.esp.connection import EspConnection


class BoardGatewayAdapter(BoardGateway):
    """Drives the relay channels of the boards over the board connection.

    Args:
        connection: Transport level board connection.

    Returns:
        None.
    """

    def __init__(self, connection: EspConnection) -> None:
        """Initialize the adapter.

        Args:
            connection: Transport level board connection.

        Returns:
            None.
        """
        self._connection = connection

    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Switch a relay and wait for the confirmation.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            channel: Physical relay channel.
            energized: True to close the contact, False to release it.

        Returns:
            BoardCommandResult: What the board answered.
        """
        accepted, reason = await self._connection.set_relay(user_id, board_id, channel, energized)
        return BoardCommandResult(accepted=accepted, reason=reason)

    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Ask a board to resend everything it knows.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        await self._connection.request_state(user_id, board_id)

    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        """Tell a board which network it is to use.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            profile: Network the board is to use.

        Returns:
            BoardCommandResult: What the board answered.
        """
        accepted, reason = await self._connection.set_network(user_id, board_id, profile)
        return BoardCommandResult(accepted=accepted, reason=reason)


class EspMicrophoneAdapter(MicrophonePort):
    """Opens and closes the microphone of a board over the board connection.

    Args:
        connection: Transport level board connection.

    Returns:
        None.
    """

    def __init__(self, connection: EspConnection) -> None:
        """Initialize the adapter.

        Args:
            connection: Transport level board connection.

        Returns:
            None.
        """
        self._connection = connection

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
        return await self._connection.arm_microphone(user_id, board_id, sample_rate, max_sec)

    async def disarm(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Stop a board from streaming audio.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the request reached the board.
        """
        return await self._connection.disarm_microphone(user_id, board_id)

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
        return await self._connection.set_speech_threshold(user_id, board_id, threshold)

    async def play(self, user_id: UserId, board_id: EspDeviceId, audio: bytes) -> bool:
        """Play an answer on the speaker of a board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            audio: Rendered audio of the phrase.

        Returns:
            bool: True when the audio reached the board.
        """
        return await self._connection.play_audio(user_id, board_id, audio)
