"""Rule based parameter extraction.

Extraction is a separate stage from classification: intent first, then the
parameters, using regular expressions and keyword dictionaries. No language model
is involved.
"""

from __future__ import annotations

import re

from smart_home_backend.application.interface.services import (
    CommandParser,
    IntentPrediction,
    ParsedCommand,
)

NUMBER_PATTERN = re.compile(r"(\d{1,3}(?:[.,]\d+)?)")

TEMPERATURE_MARKERS = ("градус", "температ", "°")
HUMIDITY_MARKERS = ("влажн", "процент", "%")
AREA_MARKERS = ("комнат", "дом", "помещен")

DEVICE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "light": ("свет", "лампа", "лампочка", "люстра", "подсветка"),
    "air_conditioner": ("кондиционер", "кондей", "сплит", "кондер"),
    "humidifier": ("увлажнитель", "увлажнить", "увлажнения"),
    "fan": ("вентилятор", "проветрить", "вентилятором"),
    "heater": ("обогреватель", "обогрев", "батарея", "обогреть"),
}

RELATIVE_TIME_WORDS: dict[str, int] = {
    "полчаса": 30,
    "полчасика": 30,
    "час": 60,
    "часа": 120,
    "часов": 60,
    "минут": 1,
    "мин": 1,
    "минуту": 1,
}

MIN_TEMPERATURE = -10.0
MAX_TEMPERATURE = 60.0
MIN_HUMIDITY = 0.0
MAX_HUMIDITY = 100.0

DEVICE_STEM_LENGTH = 4


class RuleCommandParser(CommandParser):
    """Extracts command parameters with explicit rules."""

    def parse(self, text: str, prediction: IntentPrediction) -> ParsedCommand:
        """Extract the parameters of a command.

        Args:
            text: Raw command text.
            prediction: Prediction produced by the classifier.

        Returns:
            ParsedCommand: Structured command.
        """
        normalized = re.sub(r"\s+", " ", text.lower().strip())
        return ParsedCommand(
            intent=prediction.intent,
            confidence=prediction.confidence,
            device_ref=find_device_reference(normalized),
            temperature=find_temperature(normalized),
            humidity=find_humidity(normalized),
            duration_minutes=find_duration_minutes(normalized),
            target=find_target(normalized),
            raw_text=text,
        )


def find_temperature(text: str) -> float | None:
    """Return the temperature mentioned in the text.

    Args:
        text: Normalized command text.

    Returns:
        float | None: Temperature or None when the text has none.
    """
    if not any(marker in text for marker in TEMPERATURE_MARKERS):
        return None
    match = NUMBER_PATTERN.search(text)
    if match is None:
        return None
    value = _to_float(match.group(1))
    return value if MIN_TEMPERATURE <= value <= MAX_TEMPERATURE else None


def find_humidity(text: str) -> float | None:
    """Return the humidity mentioned in the text.

    Args:
        text: Normalized command text.

    Returns:
        float | None: Humidity or None when the text has none.
    """
    if not any(marker in text for marker in HUMIDITY_MARKERS):
        return None
    match = NUMBER_PATTERN.search(text)
    if match is None:
        return None
    value = _to_float(match.group(1))
    return value if MIN_HUMIDITY <= value <= MAX_HUMIDITY else None


def find_duration_minutes(text: str) -> int | None:
    """Return the relative delay mentioned in the text.

    Args:
        text: Normalized command text.

    Returns:
        int | None: Delay in minutes or None when the text has none.
    """
    explicit = re.search(r"через\s+(\d{1,3})\s*(час|минут|мин|ч\b|м\b)", text)
    if explicit:
        amount = int(explicit.group(1))
        unit = explicit.group(2)
        return amount * 60 if unit.startswith("час") or unit == "ч" else amount
    word = re.search(r"через\s+(\w+)", text)
    if word:
        return RELATIVE_TIME_WORDS.get(word.group(1))
    return None


def find_device_reference(text: str) -> str | None:
    """Return the device word mentioned in the text.

    Words are matched by stem so that inflected Russian forms are recognized:
    "лампа", "лампу" and "лампочку" all match the same reference. The matched
    word is returned as is, because the device is resolved by its own name or
    type later on.

    Args:
        text: Normalized command text.

    Returns:
        str | None: Matched device word or None when the text has none.
    """
    words = text.split()
    for keywords in DEVICE_KEYWORDS.values():
        for word in words:
            if any(_shares_stem(word, keyword) for keyword in keywords):
                return word
    return None


def _shares_stem(word: str, keyword: str) -> bool:
    common = min(len(word), len(keyword), DEVICE_STEM_LENGTH)
    return common > 0 and word[:common] == keyword[:common]


def find_target(text: str) -> str | None:
    """Return the target area mentioned in the text.

    Args:
        text: Normalized command text.

    Returns:
        str | None: Target name or None when the text has none.
    """
    return "room" if any(marker in text for marker in AREA_MARKERS) else None


def _to_float(token: str) -> float:
    return float(token.replace(",", "."))
