"""Speech services of the smart home smart_home.

Three small clients, three ports: ``recognizer`` turns audio into text,
``synthesizer`` turns text into audio and ``understanding`` turns a transcribed
sentence into a structured command. Audio travels as raw bytes in both
directions, never as base64 inside a JSON document.

There is no process management here. The models need a machine of their own and
starting them is the job of Docker Compose or systemd, not of a web request
handler; the backend only speaks to whatever address the configuration names.
"""

from smart_home.infrastructure.voice.recognizer import (
    HttpSpeechRecognizer,
    UnavailableSpeechRecognizer,
)
from smart_home.infrastructure.voice.session import BufferedVoiceSession
from smart_home.infrastructure.voice.synthesizer import HttpSpeechSynthesizer
from smart_home.infrastructure.voice.understanding import SpokenUnderstandingAdapter

__all__ = [
    "BufferedVoiceSession",
    "HttpSpeechRecognizer",
    "HttpSpeechSynthesizer",
    "SpokenUnderstandingAdapter",
    "UnavailableSpeechRecognizer",
]
