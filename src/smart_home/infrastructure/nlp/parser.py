"""Reading the parameters out of a sentence.

Extraction is a separate stage from classification. The classifier decides *what*
was asked for; this module decides *with what*: the number, the delay, the
device and the capability, each as the typed value the application expects rather
than as a raw number a caller has to guess the unit of.

The words it matches come from :mod:`smart_home.infrastructure.nlp.vocabulary` and
from nowhere else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from smart_home.domain.climate.humidity import Humidity
from smart_home.domain.climate.temperature import Temperature
from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device_kind import DeviceKind
from smart_home.domain.exceptions import InvalidHumidityError, InvalidTemperatureError
from smart_home.infrastructure.nlp import vocabulary

WHITESPACE = re.compile(r"\s+")
NUMBER = re.compile(r"(\d{1,3}(?:[.,]\d+)?)")
REPEATED_NUMBER = re.compile(r"\d{1,3}\s+")
WORD_NUMBERS: dict[str, int] = {
    "ноль": 0,
    "один": 1,
    "одну": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "пятнадцать": 15,
    "восемнадцать": 18,
    "двадцать": 20,
    "двадцать два": 22,
    "двадцать три": 23,
    "двадцать пять": 25,
    "тридцать": 30,
}


@dataclass(frozen=True, slots=True)
class SentenceFacts:
    """What could be read out of a sentence before any model was asked.

    Args:
        device_name: Device word found in the sentence.
        device_kinds: Device kinds the sentence could be about.
        capability: Capability the sentence asks for.
        temperature: Requested temperature, rejected when it is impossible.
        humidity: Requested humidity, rejected when it is impossible.
        delay_minutes: Requested delay before a scenario starts.
        target: Requested area.

    Returns:
        None.
    """

    device_name: str | None = None
    device_kinds: frozenset[DeviceKind] = frozenset()
    capability: Capability | None = None
    temperature: Temperature | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None


class SentenceParser:
    """Reads numbers, durations and device references out of a sentence."""

    def parse(self, text: str) -> SentenceFacts:
        """Read everything a sentence carries.

        Args:
            text: Raw sentence as typed or as transcribed.

        Returns:
            SentenceFacts: Typed values found in the sentence.
        """
        normalized = normalize(text)
        kinds = vocabulary.kinds_in(normalized)
        return SentenceFacts(
            device_name=_device_word(normalized) if kinds else None,
            device_kinds=kinds,
            capability=vocabulary.capability_in(normalized),
            temperature=_temperature(normalized),
            humidity=_humidity(normalized),
            delay_minutes=vocabulary.duration_in(normalized),
            target=vocabulary.area_in(normalized),
        )


def normalize(text: str) -> str:
    """Return a sentence in the shape the vocabulary matches.

    Args:
        text: Raw sentence as typed or as transcribed.

    Returns:
        str: Lowercased sentence with single spaces and no punctuation.
    """
    cleaned = "".join(
        " " if not character.isalnum() and character not in "%°" else character
        for character in text.lower()
    )
    return WHITESPACE.sub(" ", cleaned).strip()


def _device_word(text: str) -> str | None:
    for word in text.split():
        if any(
            vocabulary.shares_prefix(word, keyword)
            for keywords in vocabulary.DEVICE_KIND_WORDS.values()
            for keyword in keywords
        ):
            return word
    return None


def _first_number(text: str) -> float | None:
    match = NUMBER.search(REPEATED_NUMBER.sub(" ", text))
    if match is not None:
        return float(match.group(1).replace(",", "."))
    for word in text.split():
        spelled = WORD_NUMBERS.get(word)
        if spelled is not None:
            return float(spelled)
    return None


def _temperature(text: str) -> Temperature | None:
    if not any(vocabulary.mentions(text, (marker,)) for marker in vocabulary.TEMPERATURE_MARKERS):
        return None
    value = _first_number(text)
    if value is None:
        return None
    try:
        return Temperature(value)
    except InvalidTemperatureError:
        return None


def _humidity(text: str) -> float | None:
    if not any(vocabulary.mentions(text, (marker,)) for marker in vocabulary.HUMIDITY_MARKERS):
        return None
    value = _first_number(text)
    if value is None:
        return None
    try:
        return Humidity(value).percent
    except InvalidHumidityError:
        return None
