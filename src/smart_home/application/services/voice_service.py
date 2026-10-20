"""Voice pipeline of one account.

Three ways in, one path out: a typed sentence, a recording from a browser and the
microphone of a board all end up in the same command dispatcher, so the answer a
person hears is the answer the interface would have shown.

The service owns no audio detail. Buffering, byte limits and decoding happen
behind the ports, which is why there is no sample rate arithmetic and no partially
received phrase anywhere near a business rule.
"""

from __future__ import annotations

from dataclasses import dataclass

from smart_home.application.errors import CommandNotUnderstoodError
from smart_home.application.ports.boards import MicrophonePort, MicrophoneStream
from smart_home.application.ports.voice import (
    AudioClip,
    ReplyComposer,
    SpeechRecognizer,
    SpeechSynthesizer,
    VoiceSession,
    VoiceUnavailableError,
)
from smart_home.application.services.command_dispatcher import CommandDispatcher
from smart_home.domain.identifiers import EspDeviceId, UserId


@dataclass(frozen=True, slots=True)
class VoiceReply:
    """What the voice channel produced.

    Args:
        transcript: Text that was recognized, empty when nothing was said.
        answer: Phrase for the user.
        audio: Rendered audio of the answer, empty when synthesis is off.
        was_a_command: True when the phrase was carried out as a command.

    Returns:
        None.
    """

    transcript: str
    answer: str
    audio: bytes = b""
    was_a_command: bool = False


class VoiceCommandService(MicrophoneStream):
    """Turns speech into a command and the result of that command back into speech."""

    def __init__(
        self,
        dispatcher: CommandDispatcher,
        sessions: VoiceSession,
        recognizer: SpeechRecognizer | None,
        synthesizer: SpeechSynthesizer | None,
        microphone: MicrophonePort,
        composer: ReplyComposer,
        sample_rate: int,
        max_audio_sec: int,
    ) -> None:
        """Initialize the service.

        Args:
            dispatcher: Command bus carrying out what was said. Its understanding
                port already prefers the remote model and falls back to the local
                pipeline, so speech and typed text reach the very same handlers.
            sessions: Collects the microphone stream into phrases.
            recognizer: Speech recognition, or None when it is switched off.
            synthesizer: Speech synthesis, or None when it is switched off.
            microphone: Opens the microphone of a board and plays answers on it.
            composer: Builds the wording of the answers.
            sample_rate: Sample rate the boards are told to use.
            max_audio_sec: Longest phrase a board may send.

        Returns:
            None.
        """
        self._dispatcher = dispatcher
        self._sessions = sessions
        self._recognizer = recognizer
        self._synthesizer = synthesizer
        self._microphone = microphone
        self._composer = composer
        self._sample_rate = sample_rate
        self._max_audio_sec = max_audio_sec
        self._last_audio: dict[UserId, bytes] = {}

    @property
    def is_recognizing(self) -> bool:
        """Return whether speech recognition is available.

        Returns:
            bool: True when a recognizer was configured.
        """
        return self._recognizer is not None

    @property
    def sample_rate(self) -> int:
        """Return the sample rate the boards are told to use.

        Returns:
            int: Samples per second.
        """
        return self._sample_rate

    async def run_text(self, user_id: UserId, text: str) -> VoiceReply:
        """Carry out a sentence as if it had been spoken.

        Args:
            user_id: Owner the command is executed for.
            text: Sentence to run.

        Returns:
            VoiceReply: What carrying the command out produced.
        """
        answer = await self._carry_out(user_id, text)
        return await self._speak(user_id, "", answer, was_a_command=True)

    async def run_clip(self, user_id: UserId, samples: bytes) -> VoiceReply:
        """Recognize a recording and carry out what it says.

        Args:
            user_id: Owner the command is executed for.
            samples: Raw samples of the phrase.

        Returns:
            VoiceReply: Transcript, answer and the result of the command.

        Raises:
            VoiceUnavailableError: When recognition is switched off or down.
        """
        if self._recognizer is None:
            raise VoiceUnavailableError(self._composer.for_unavailable_service())
        transcript = await self._recognizer.transcribe(
            AudioClip(samples=samples, sample_rate=self._sample_rate)
        )
        if not transcript.text.strip():
            return await self._speak(user_id, "", self._composer.for_missing_speech())
        answer = await self._carry_out(user_id, transcript.text)
        return await self._speak(user_id, transcript.text, answer, was_a_command=True)

    async def on_started(self, user_id: UserId, board_id: EspDeviceId, sample_rate: int) -> None:
        """Start collecting a phrase from a board.

        Args:
            user_id: Owner of the board that is streaming.
            board_id: Identifier of the board.
            sample_rate: Samples per second the board streams with.

        Returns:
            None.
        """
        del board_id
        await self._sessions.begin(user_id, sample_rate)

    async def on_samples(self, user_id: UserId, board_id: EspDeviceId, samples: bytes) -> None:
        """Accept the next piece of a phrase from a board.

        Args:
            user_id: Owner of the board that is streaming.
            board_id: Identifier of the board.
            samples: Raw samples of the piece.

        Returns:
            None.
        """
        del board_id
        await self._sessions.feed(user_id, samples)

    async def on_stopped(self, user_id: UserId, board_id: EspDeviceId, reason: str) -> None:
        """Close the phrase and answer on the board that streamed it.

        Args:
            user_id: Owner of the board that was streaming.
            board_id: Identifier of the board.
            reason: Why the board stopped.

        Returns:
            None.
        """
        transcript = await self._sessions.finish(user_id, reason)
        if transcript is None or not transcript.text.strip():
            return
        answer = await self._carry_out(user_id, transcript.text)
        reply = await self._speak(user_id, transcript.text, answer, was_a_command=True)
        if reply.audio:
            await self._microphone.play(user_id, board_id, reply.audio)

    async def arm(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Let a board stream the next phrase.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the request reached the board.
        """
        return await self._microphone.arm(user_id, board_id, self._sample_rate, self._max_audio_sec)

    async def disarm(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Stop a board from streaming audio.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when the request reached the board.
        """
        return await self._microphone.disarm(user_id, board_id)

    async def last_audio(self, user_id: UserId) -> bytes:
        """Return the audio of the last answer, when synthesis is switched on.

        Args:
            user_id: Owner the answer belongs to.

        Returns:
            bytes: Rendered audio, empty when there is nothing to play.
        """
        return self._last_audio.get(user_id, b"")

    async def _carry_out(self, user_id: UserId, text: str) -> str:
        try:
            reply = await self._dispatcher.dispatch(user_id, text)
        except CommandNotUnderstoodError as refusal:
            return refusal.reason.value.replace("_", " ").lower()
        except VoiceUnavailableError:
            return self._composer.for_unavailable_service()
        return reply.answer or self._composer.for_result(reply)

    async def _speak(
        self, user_id: UserId, transcript: str, answer: str, *, was_a_command: bool
    ) -> VoiceReply:
        audio = b""
        if self._synthesizer is not None and answer:
            try:
                audio = await self._synthesizer.synthesize(answer)
            except VoiceUnavailableError:
                audio = b""
        self._last_audio[user_id] = audio
        return VoiceReply(
            transcript=transcript, answer=answer, audio=audio, was_a_command=was_a_command
        )
