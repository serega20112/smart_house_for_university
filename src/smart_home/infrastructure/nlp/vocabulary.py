"""Every word the pipeline knows, in one place.

Russian is the language this system answers in, so the words a person may say
live here and nowhere else. The model deliberately knows no vocabulary: reading
"кондиционер" as a hint about the air conditioner belongs to the adapter that
knows the language, and the domain only ever compares names it is given.

The module is deliberately plain data. Words are matched by their first
characters rather than by a stemmer, because Russian inflects both nouns and
verbs and a four character prefix is what stays stable across the forms a person
actually uses.
"""

from __future__ import annotations

from typing import Final

from smart_home.application.ports.language import Intent
from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device_kind import DeviceKind

PREFIX_LENGTH: Final = 4

ON_WORDS: Final[tuple[str, ...]] = (
    "включи",
    "включить",
    "включай",
    "врубай",
    "врубать",
    "зажги",
    "зажгите",
    "запусти",
    "запустить",
    "дай",
    "подай",
    "восстанови",
)

OFF_WORDS: Final[tuple[str, ...]] = (
    "выключи",
    "выключить",
    "выключай",
    "вырубай",
    "вырубать",
    "погаси",
    "потуши",
    "останови",
    "остановь",
    "отключи",
    "убавь",
)

EVERYTHING_WORDS: Final[tuple[str, ...]] = (
    "все",
    "всё",
    "всего",
    "каждый",
    "каждую",
    "все устройства",
)

COOL_WORDS: Final[tuple[str, ...]] = (
    "охлади",
    "охлаждай",
    "охладить",
    "прохладнее",
    "прохладно",
    "холоднее",
    "холодно",
    "жарко",
)

HEAT_WORDS: Final[tuple[str, ...]] = (
    "нагрей",
    "нагревай",
    "нагреть",
    "теплее",
    "тепло",
    "холодно",
    "прохладно",
)

HUMIDIFY_WORDS: Final[tuple[str, ...]] = (
    "увлажни",
    "увлажнить",
    "увлажняй",
    "увлажнение",
    "сухо",
)

DEHUMIDIFY_WORDS: Final[tuple[str, ...]] = (
    "осуши",
    "осушить",
    "высуши",
    "влажно",
    "сыро",
)

CANCEL_WORDS: Final[tuple[str, ...]] = (
    "отмени",
    "отмена",
    "отменить",
    "откати",
    "убери",
    "аннулируй",
    "прекрати",
)

DESCRIBE_WORDS: Final[tuple[str, ...]] = (
    "состояние",
    "статус",
    "обстановка",
    "что включено",
    "что происходит",
    "покажи",
    "расскажи",
)

SCHEDULE_WORDS: Final[tuple[str, ...]] = (
    "через",
    "когда",
    "позже",
    "потом",
    "запланируй",
    "запланировать",
    "таймер",
    "по расписанию",
)

TEMPERATURE_MARKERS: Final[tuple[str, ...]] = (
    "градус",
    "температур",
    "темпера",
    "°",
    "теплее",
    "холоднее",
    "прохладнее",
)

HUMIDITY_MARKERS: Final[tuple[str, ...]] = (
    "влажн",
    "процент",
    "%",
)

AREA_WORDS: Final[tuple[str, ...]] = (
    "комнат",
    "дом",
    "помещен",
    "кухн",
    "спальн",
    "гостин",
    "прихож",
    "кабинет",
)

DEVICE_KIND_WORDS: Final[dict[DeviceKind, tuple[str, ...]]] = {
    DeviceKind.LIGHT: ("свет", "лампа", "ламп", "люстр", "подсвет", "торшер"),
    DeviceKind.FAN: ("вентилятор", "вентил", "проветр"),
    DeviceKind.HUMIDIFIER: ("увлажнитель", "увлажнит", "увлажнен"),
    DeviceKind.DEHUMIDIFIER: ("осушитель", "осуш", "сушилк"),
    DeviceKind.AIR_CONDITIONER: ("кондиционер", "кондей", "сплит", "кондер"),
    DeviceKind.HEATER: ("обогреватель", "обогрев", "батаре", "радиатор", "теплов"),
    DeviceKind.OUTLET: ("розетк", "розетка", "прибор", "техник"),
}

CAPABILITY_WORDS: Final[dict[Capability, tuple[str, ...]]] = {
    Capability.ON: ON_WORDS,
    Capability.OFF: OFF_WORDS,
    Capability.COOL: COOL_WORDS,
    Capability.HEAT: HEAT_WORDS,
    Capability.HUMIDIFY: HUMIDIFY_WORDS,
    Capability.DEHUMIDIFY: DEHUMIDIFY_WORDS,
}

DURATION_WORDS: Final[dict[str, int]] = {
    "полчаса": 30,
    "полчасика": 30,
    "час": 60,
    "часа": 60,
    "часов": 60,
    "минут": 1,
    "минуту": 1,
    "минуты": 1,
    "мин": 1,
    "м": 1,
}

INTENT_REFERENCES: Final[dict[Intent, tuple[str, ...]]] = {
    Intent.SWITCH_DEVICE: (
        "включи свет",
        "зажги лампу",
        "включи лампочку",
        "включи кондиционер",
        "запусти вентилятор",
        "включи увлажнитель",
        "включи обогреватель",
        "дай свет",
        "врубай свет",
        "выключи свет",
        "потуши свет",
        "выключи кондиционер",
        "останови вентилятор",
        "выключи лампу",
        "погаси свет",
        "выключи увлажнитель",
        "выключи обогреватель",
    ),
    Intent.SWITCH_ALL: (
        "включи всё",
        "выключи всё",
        "потуши всё",
        "включи все устройства",
        "вырубай все устройства",
        "полностью выключи свет",
        "обесточь всё",
        "зажги всё",
        "врубай всё",
    ),
    Intent.SET_TEMPERATURE: (
        "сделай 20 градусов",
        "поставь температуру 22",
        "установи 24 градуса",
        "температура 21",
        "сделай 25 градусов в комнате",
        "нагрей до 23",
        "поставь двадцать градусов",
    ),
    Intent.SET_HUMIDITY: (
        "сделай влажность 45 процентов",
        "поставь влажность 50",
        "увлажни комнату до 55",
        "влажность 40 процентов",
        "поставь влажность 60 процентов",
    ),
    Intent.RUN_CAPABILITY: (
        "тут жарко",
        "сделай прохладнее",
        "охлади комнату",
        "понизь температуру",
        "что-то жарковато",
        "слишком тепло",
        "тут холодно",
        "подними температуру",
        "сделай теплее",
        "погреть комнату",
        "слишком сухо",
        "слишком влажно",
    ),
    Intent.DESCRIBE_HOME: (
        "какое состояние",
        "статус дома",
        "что сейчас включено",
        "как обстановка",
        "покажи состояние",
        "что происходит дома",
    ),
    Intent.READ_TEMPERATURE: (
        "какая температура",
        "сколько градусов",
        "температура в комнате",
        "на сколько тепло",
        "как холодно",
    ),
    Intent.READ_HUMIDITY: (
        "какая влажность",
        "сколько процентов влажность",
        "влажность в комнате",
        "сухо или мокро",
    ),
    Intent.SCHEDULE_SCENARIO: (
        "через полчаса сделай 20 градусов",
        "через час сделай 22 градуса",
        "поставь таймер на 20 градусов через 30 минут",
        "через полчаса сделай прохладно",
        "запланируй охлаждение на потом",
    ),
    Intent.CANCEL_SCENARIO: (
        "отмени сценарий",
        "убери таймер",
        "отмени задачу",
        "аннулируй сценарий",
        "прекрати сценарий",
    ),
}


def reference_pairs() -> tuple[tuple[str, str], ...]:
    """Return the reference phrases flattened into intent and phrase pairs.

    Returns:
        tuple[tuple[str, str], ...]: Intent names paired with their phrases, in a
        stable order so a re-seed never rewrites a row it already stored.
    """
    return tuple(
        (intent.value, phrase) for intent in Intent for phrase in INTENT_REFERENCES.get(intent, ())
    )


def shares_prefix(word: str, keyword: str) -> bool:
    """Return whether two Russian words are the same word in different cases.

    Args:
        word: Word taken from the sentence.
        keyword: Word this vocabulary knows.

    Returns:
        bool: True when the two share their leading characters.
    """
    length = min(len(word), len(keyword), PREFIX_LENGTH)
    return length > 0 and word[:length] == keyword[:length]


def mentions(text: str, words: tuple[str, ...]) -> bool:
    """Return whether a sentence carries one of the given words.

    A keyword containing a space is matched as a phrase; a single word is matched
    by its prefix, which is what makes "включи", "включить" and "включая" one
    word to this vocabulary.

    Args:
        text: Normalized sentence.
        words: Words this vocabulary knows.

    Returns:
        bool: True when at least one word was found.
    """
    if any(" " in keyword and keyword in text for keyword in words):
        return True
    return any(shares_prefix(word, keyword) for word in text.split() for keyword in words)


def kinds_in(text: str) -> frozenset[DeviceKind]:
    """Return the device kinds a sentence could be about.

    Args:
        text: Normalized sentence.

    Returns:
        frozenset[DeviceKind]: Kinds the sentence hints at, empty when it names
        none.
    """
    found = {
        kind
        for kind, keywords in DEVICE_KIND_WORDS.items()
        if any(mentions(text, (keyword,)) for keyword in keywords)
    }
    return frozenset(found)


def capability_in(text: str) -> Capability | None:
    """Return the capability a sentence asks for.

    The negative words win over the positive ones, because "выключи свет"
    contains no positive verb yet means the very opposite of "включи свет".

    Args:
        text: Normalized sentence.

    Returns:
        Capability | None: Capability the sentence asks for, or None when it asks
        for none.
    """
    for capability in (Capability.OFF, Capability.DEHUMIDIFY, Capability.HUMIDIFY):
        if mentions(text, CAPABILITY_WORDS[capability]):
            return capability
    for capability in (Capability.ON, Capability.COOL, Capability.HEAT):
        if mentions(text, CAPABILITY_WORDS[capability]):
            return capability
    return None


def duration_in(text: str) -> int | None:
    """Return the delay a sentence asks for, in minutes.

    Args:
        text: Normalized sentence.

    Returns:
        int | None: Delay in minutes, or None when the sentence names no delay.
    """
    if not mentions(text, SCHEDULE_WORDS):
        return None
    for word in text.split():
        minutes = DURATION_WORDS.get(word)
        if minutes is not None:
            return minutes
    return None


def area_in(text: str) -> str | None:
    """Return the area a sentence names.

    Args:
        text: Normalized sentence.

    Returns:
        str | None: Area name, or None when the sentence names none.
    """
    for word in text.split():
        if any(shares_prefix(word, keyword) for keyword in AREA_WORDS):
            return word
    return None


def switch_everything(text: str) -> bool:
    """Return whether a sentence addresses every device of the home.

    Args:
        text: Normalized sentence.

    Returns:
        bool: True when the sentence names the whole home.
    """
    return mentions(text, EVERYTHING_WORDS)
