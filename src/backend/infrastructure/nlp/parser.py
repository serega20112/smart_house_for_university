"""Вынимает параметры из предложения.

Выписывание — отдельная стадия, не смешанная с классификацией. Классификатор решает
*что* попросили; этот модуль решает *чем*: число, задержку, устройство и способность —
каждое тем типизированным значением, которого ждёт приложение, а не голым числом, к
которому вызывающему надо самому догадаться о единице измерения.

Слова для сравнения берутся из :mod:`backend.infrastructure.nlp.vocabulary` и больше
ниоткуда.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.domain.exceptions import InvalidHumidityError, InvalidTemperatureError
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.infrastructure.nlp import vocabulary

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
    """Что удалось прочитать из предложения, ещё не спрашивая ни одну модель.

    Attributes:
        device_name: Слово об устройстве, найденное в предложении.
        device_kinds: Назначения устройств, о которых могло идти речь.
        capability: Способность, о которой просит предложение.
        temperature: Запрошенная температура; невозможную модель не принимает.
        humidity: Запрошенная влажность; невозможную модель не принимает.
        delay_minutes: Запрошенная задержка перед началом сценария.
        target: Запрошенное место.
    """

    device_name: str | None = None
    device_kinds: frozenset[DeviceKind] = frozenset()
    capability: Capability | None = None
    temperature: Temperature | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None


class SentenceParser:
    """Вычитывает из предложения числа, длительности и ссылки на устройства."""

    def parse(self, text: str) -> SentenceFacts:
        """Вычитывает всё, что есть в предложении.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            SentenceFacts: Типизированные значения, найденные в предложении.
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
    """Приводит предложение к виду, с которым сравнивает словарь.

    Args:
        text: Предложение в сыром виде, каким его получил интерфейс.

    Returns:
        str: Предложение в нижнем регистре, с одинарными пробелами и без знаков
            препинания.
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
