"""Microphone to command pipeline.

The pipeline is exercised without any model: a stub recognizer stands in for the
machine running Whisper, and the command use case is recorded, which proves that
a spoken phrase ends up in the very same place a typed one does.
"""

from __future__ import annotations

from typing import Any

import pytest

from smart_home_backend.application.dto.command import CommandResult
from smart_home_backend.application.interface.services import (
    AudioClip,
    MicControl,
    ReplyComposer,
    SpeechRecognizer,
    SpeechSynthesizer,
    Transcript,
    VoiceUnavailableError,
)
from smart_home_backend.application.services import (
    NO_SPEECH,
    VOICE_UNAVAILABLE,
    VoiceCommandRouter,
)
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.domain.value_objects.identity import UserId

SAMPLE_RATE = 16000
PHRASE = bytes(6000)
FIRST = UserId("550e8400-e29b-41d4-a716-446655440000")
SECOND = UserId("550e8400-e29b-41d4-a716-446655440001")


class ScriptedRecognizer(SpeechRecognizer):
    """Recognizer answering with a prepared transcript."""

    def __init__(self, text: str = "включи свет", error: bool = False) -> None:
        """Initialize the stub.

        Args:
            text: Text the recognizer reports.
            error: Whether the recognizer pretends to be unavailable.

        Returns:
            None.
        """
        self.text = text
        self.error = error
        self.clips: list[AudioClip] = []

    async def transcribe(self, clip: AudioClip) -> Transcript:
        """Report the prepared transcript.

        Args:
            clip: Audio of the phrase.

        Returns:
            Transcript: Prepared transcript.

        Raises:
            VoiceUnavailableError: When the stub is configured to fail.
        """
        self.clips.append(clip)
        if self.error:
            raise VoiceUnavailableError("voice_service_unreachable")
        return Transcript(text=self.text)


class SilentSynthesizer(SpeechSynthesizer):
    """Synthesizer returning a fixed payload."""

    def __init__(self) -> None:
        """Initialize the stub.

        Returns:
            None.
        """
        self.spoken: list[str] = []

    async def synthesize(self, text: str) -> AudioClip | None:
        """Return the prepared payload.

        Args:
            text: Phrase to speak.

        Returns:
            AudioClip | None: Prepared audio.
        """
        self.spoken.append(text)
        return AudioClip(pcm=b"RIFF-audio", sample_rate=SAMPLE_RATE)


class RecordingMic(MicControl):
    """Microphone control remembering what a board was asked to do."""

    def __init__(self, online: bool = True) -> None:
        """Initialize the stub.

        Args:
            online: Whether a board is considered connected.

        Returns:
            None.
        """
        self.online = online
        self.armed: list[tuple[UserId, int, int]] = []
        self.disarmed: list[UserId] = []
        self.thresholds: list[tuple[UserId, int]] = []

    async def arm(self, user_id: UserId, sample_rate: int, max_sec: int) -> bool:
        """Record an arming request.

        Args:
            user_id: Owner of the board.
            sample_rate: Samples per second requested.
            max_sec: Longest phrase requested.

        Returns:
            bool: Whether a board is connected.
        """
        self.armed.append((user_id, sample_rate, max_sec))
        return self.online

    async def disarm(self, user_id: UserId) -> bool:
        """Record a disarming request.

        Args:
            user_id: Owner of the board.

        Returns:
            bool: Whether a board is connected.
        """
        self.disarmed.append(user_id)
        return self.online

    async def set_vad_threshold(self, user_id: UserId, threshold: int) -> bool:
        """Record a threshold change.

        Args:
            user_id: Owner of the board.
            threshold: Requested threshold.

        Returns:
            bool: Whether a board is connected.
        """
        self.thresholds.append((user_id, threshold))
        return self.online


class FixedComposer(ReplyComposer):
    """Composer returning recognizable strings."""

    def compose(self, result: object) -> str:
        """Return a marker of the executed command.

        Args:
            result: Structured result of the command.

        Returns:
            str: Marker text.
        """
        return f"executed:{getattr(result, 'intent', None)}"

    def compose_no_speech(self) -> str:
        """Return the marker of an empty phrase.

        Returns:
            str: Marker text.
        """
        return "nothing"

    def compose_unavailable(self) -> str:
        """Return the marker of an unavailable service.

        Returns:
            str: Marker text.
        """
        return "unavailable"


class RecordingCommands:
    """Command use case recording what it was asked to execute."""

    def __init__(self) -> None:
        """Initialize the stub.

        Returns:
            None.
        """
        self.executed: list[tuple[UserId, str]] = []

    async def execute(self, user_id: UserId, command: Any) -> CommandResult:
        """Record the command and answer with a successful result.

        Args:
            user_id: Owner the command belongs to.
            command: Command to record.

        Returns:
            CommandResult: Successful result.
        """
        self.executed.append((user_id, command.text))
        return CommandResult(status=OperationStatus.SUCCESS, intent="TURN_ON")


class RecordingEvents:
    """Event bus remembering the published moments."""

    def __init__(self) -> None:
        """Initialize the stub.

        Returns:
            None.
        """
        self.published: list[tuple[UserId, str]] = []

    async def publish(self, user_id: UserId, name: str, payload: Any) -> None:
        """Record a published event.

        Args:
            user_id: Owner the event belongs to.
            name: Name of the event.
            payload: Payload of the event.

        Returns:
            None.
        """
        self.published.append((user_id, name))


def build_router(
    commands: RecordingCommands,
    mic: RecordingMic,
    events: RecordingEvents,
    recognizer: SpeechRecognizer | None = None,
    synthesizer: SpeechSynthesizer | None = None,
    continuous: bool = False,
    max_audio_sec: int = 15,
) -> VoiceCommandRouter:
    """Build the pipeline with stubs instead of models.

    Args:
        commands: Command use case stub.
        mic: Microphone control stub.
        events: Event bus stub.
        recognizer: Speech recognition stub, or None when it is switched off.
        synthesizer: Speech synthesis stub, or None for text only answers.
        continuous: Whether listening resumes after a phrase.
        max_audio_sec: Longest phrase accepted.

    Returns:
        VoiceCommandRouter: Assembled pipeline.
    """
    return VoiceCommandRouter(
        commands=commands,
        composer=FixedComposer(),
        events=events,  # type: ignore[arg-type]
        mic=mic,
        recognizer=recognizer,
        synthesizer=synthesizer,
        sample_rate=SAMPLE_RATE,
        max_audio_sec=max_audio_sec,
        continuous=continuous,
        vad_threshold=200,
    )


@pytest.mark.asyncio
async def test_collected_phrase_reaches_the_command_use_case() -> None:
    commands = RecordingCommands()
    recognizer = ScriptedRecognizer()
    router = build_router(commands, RecordingMic(), RecordingEvents(), recognizer)
    sink = router.sink_for(FIRST)

    await sink.on_audio_started(SAMPLE_RATE)
    await sink.on_audio_chunk(PHRASE)
    await sink.on_audio_stopped("silence")
    await router.drain()

    assert commands.executed == [(FIRST, "включи свет")]
    assert recognizer.clips[0].sample_rate == SAMPLE_RATE
    assert recognizer.clips[0].pcm == PHRASE


@pytest.mark.asyncio
async def test_chunks_are_reassembled_in_order() -> None:
    commands = RecordingCommands()
    router = build_router(commands, RecordingMic(), RecordingEvents(), ScriptedRecognizer())
    sink = router.sink_for(FIRST)

    await sink.on_audio_started(SAMPLE_RATE)
    await sink.on_audio_chunk(PHRASE[:3000])
    await sink.on_audio_chunk(PHRASE[3000:])
    await sink.on_audio_stopped("silence")
    await router.drain()

    assert commands.executed == [(FIRST, "включи свет")]


@pytest.mark.asyncio
async def test_short_noise_is_not_recognized() -> None:
    commands = RecordingCommands()
    recognizer = ScriptedRecognizer()
    router = build_router(commands, RecordingMic(), RecordingEvents(), recognizer)
    sink = router.sink_for(FIRST)

    await sink.on_audio_started(SAMPLE_RATE)
    await sink.on_audio_chunk(bytes(100))
    await sink.on_audio_stopped("silence")
    await router.drain()

    assert commands.executed == []
    assert recognizer.clips == []


@pytest.mark.asyncio
async def test_chunks_outside_a_phrase_are_ignored() -> None:
    commands = RecordingCommands()
    router = build_router(commands, RecordingMic(), RecordingEvents(), ScriptedRecognizer())
    sink = router.sink_for(FIRST)

    await sink.on_audio_chunk(PHRASE)
    await sink.on_audio_stopped("silence")
    await router.drain()

    assert commands.executed == []


@pytest.mark.asyncio
async def test_phrase_of_one_account_never_reaches_another() -> None:
    commands = RecordingCommands()
    router = build_router(commands, RecordingMic(), RecordingEvents(), ScriptedRecognizer())
    first_sink = router.sink_for(FIRST)
    second_sink = router.sink_for(SECOND)

    await first_sink.on_audio_started(SAMPLE_RATE)
    await first_sink.on_audio_chunk(PHRASE)
    await second_sink.on_audio_started(SAMPLE_RATE)
    await second_sink.on_audio_chunk(bytes(200))
    await first_sink.on_audio_stopped("silence")
    await router.drain()

    assert commands.executed == [(FIRST, "включи свет")]


@pytest.mark.asyncio
async def test_silence_reports_nothing_heard() -> None:
    commands = RecordingCommands()
    router = build_router(commands, RecordingMic(), RecordingEvents(), ScriptedRecognizer())

    outcome = await router.speak(FIRST, b"")

    assert outcome.status == NO_SPEECH
    assert outcome.message == "nothing"
    assert commands.executed == []


@pytest.mark.asyncio
async def test_unreachable_recognizer_is_reported_not_raised() -> None:
    commands = RecordingCommands()
    router = build_router(
        commands, RecordingMic(), RecordingEvents(), ScriptedRecognizer(error=True)
    )

    outcome = await router.speak(FIRST, PHRASE)

    assert outcome.status == VOICE_UNAVAILABLE
    assert outcome.message == "unavailable"
    assert commands.executed == []


@pytest.mark.asyncio
async def test_pipeline_without_recognizer_reports_unavailable() -> None:
    router = build_router(RecordingCommands(), RecordingMic(), RecordingEvents())

    outcome = await router.speak(FIRST, PHRASE)

    assert outcome.status == VOICE_UNAVAILABLE
    assert router.active is False


@pytest.mark.asyncio
async def test_answer_is_spoken_and_kept_for_the_interface() -> None:
    commands = RecordingCommands()
    synthesizer = SilentSynthesizer()
    router = build_router(
        commands,
        RecordingMic(),
        RecordingEvents(),
        ScriptedRecognizer(),
        synthesizer,
    )

    outcome = await router.speak(FIRST, PHRASE)

    assert outcome.status == "SUCCESS"
    assert outcome.message == "executed:TURN_ON"
    assert synthesizer.spoken == ["executed:TURN_ON"]
    assert router.last_reply(FIRST) == outcome
    assert router.last_reply(SECOND) is None


@pytest.mark.asyncio
async def test_arming_sends_the_configured_rate_and_threshold() -> None:
    mic = RecordingMic()
    router = build_router(RecordingCommands(), mic, RecordingEvents())

    assert await router.arm(FIRST) is True

    assert mic.armed == [(FIRST, SAMPLE_RATE, 15)]
    assert mic.thresholds == [(FIRST, 200)]


@pytest.mark.asyncio
async def test_listening_resumes_after_a_phrase_in_continuous_mode() -> None:
    mic = RecordingMic()
    router = build_router(
        RecordingCommands(), mic, RecordingEvents(), ScriptedRecognizer(), continuous=True
    )
    sink = router.sink_for(FIRST)

    await sink.on_audio_started(SAMPLE_RATE)
    await sink.on_audio_chunk(PHRASE)
    await sink.on_audio_stopped("silence")
    await router.drain()

    assert mic.armed == [(FIRST, SAMPLE_RATE, 15)]


@pytest.mark.asyncio
async def test_offline_board_is_reported_by_arming() -> None:
    router = build_router(RecordingCommands(), RecordingMic(online=False), RecordingEvents())

    assert await router.arm(FIRST) is False


@pytest.mark.asyncio
async def test_phrase_longer_than_the_limit_is_truncated() -> None:
    commands = RecordingCommands()
    recognizer = ScriptedRecognizer()
    router = build_router(
        commands,
        RecordingMic(),
        RecordingEvents(),
        recognizer,
        max_audio_sec=1,
    )
    sink = router.sink_for(FIRST)

    await sink.on_audio_started(SAMPLE_RATE)
    await sink.on_audio_chunk(bytes(SAMPLE_RATE * 4))
    await sink.on_audio_stopped("limit")
    await router.drain()

    assert len(recognizer.clips[0].pcm) == SAMPLE_RATE * 2


@pytest.mark.asyncio
async def test_transcript_and_result_are_published_for_the_interface() -> None:
    events = RecordingEvents()
    router = build_router(RecordingCommands(), RecordingMic(), events, ScriptedRecognizer())

    await router.speak(FIRST, PHRASE)

    assert (FIRST, "voice.transcript") in events.published
    assert (FIRST, "voice.result") in events.published