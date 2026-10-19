"""Speech services of the smart home backend.

Three small clients, three ports: ``recognizer`` turns audio into text,
``synthesizer`` turns text into audio and ``understanding`` turns a transcribed
sentence into a structured command. Audio travels as raw bytes in both
directions, never as base64 inside a JSON document.

There is no process management here. The models need a machine of their own and
starting them is the job of Docker Compose or systemd, not of a web request
handler; the backend only speaks to whatever address the configuration names.
"""

from backend.infrastructure.voice.recognizer import (
    HttpSpeechRecognizer,
    UnavailableSpeechRecognizer,
)
from backend.infrastructure.voice.session import BufferedVoiceSession
from backend.infrastructure.voice.synthesizer import HttpSpeechSynthesizer
from backend.infrastructure.voice.understanding import SpokenUnderstandingAdapter

__all__ = [
    "BufferedVoiceSession",
    "HttpSpeechRecognizer",
    "HttpSpeechSynthesizer",
    "SpokenUnderstandingAdapter",
    "UnavailableSpeechRecognizer",
]
