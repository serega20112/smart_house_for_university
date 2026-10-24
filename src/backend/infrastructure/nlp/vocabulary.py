"""Все слова, которые знает конвейер, в одном месте.

Русский — язык, на котором система отвечает, поэтому слова, которые может сказать
человек, живут здесь и больше нигде. Модель нарочно словаря не знает: прочитать
«кондиционер» как намёк на нужное устройство — дело адаптера, знающего язык, а домен
сравнивает только переданные ему имена.

Модуль нарочно простые данные. Слова сравнивают по первым символам, а не степпером:
русский склоняет и существительные, и глаголы, и устойчивым остаётся четырёхсимвольная
приставка — та самая, которая сквозит во всех формах, которыми человек реально пользуется.
"""

from __future__ import annotations

from typing import Final

from backend.application.dto.language.intent import Intent
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind

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
    """Возвращает опорные фразы, разложенные на пары «намерение и фраза».

    Returns:
        tuple[tuple[str, str], ...]: Названия намерений со своими фразами, в устойчивом
        порядке, чтобы повторное наполнение не переписывало уже сохранённую строку.
    """
    return tuple(
        (intent.value, phrase) for intent in Intent for phrase in INTENT_REFERENCES.get(intent, ())
    )


def shares_prefix(word: str, keyword: str) -> bool:
    """Сообщает, одно ли это русское слово в разных падежах.

    Args:
        word: Слово, взятое из предложения.
        keyword: Слово, которое знает этот словарь.

    Returns:
        bool: True, когда оба слова совпадают началом.
    """
    length = min(len(word), len(keyword), PREFIX_LENGTH)
    return length > 0 and word[:length] == keyword[:length]


def mentions(text: str, words: tuple[str, ...]) -> bool:
    """Сообщает, есть ли в предложении одно из данных слов.

    Ключевое слово с пробелом ищется как фраза целиком, а одиночное слово — по
    приставке: именно поэтому для этого словаря «включи», «включить» и «включая» —
    одно слово.

    Args:
        text: Приведённое предложение.
        words: Слова, которые знает этот словарь.

    Returns:
        bool: True, когда хотя бы одно слово нашлось.
    """
    if any(" " in keyword and keyword in text for keyword in words):
        return True
    return any(shares_prefix(word, keyword) for word in text.split() for keyword in words)


def kinds_in(text: str) -> frozenset[DeviceKind]:
    """Возвращает назначения устройств, о которых могло идти речь в предложении.

    Args:
        text: Приведённое предложение.

    Returns:
        frozenset[DeviceKind]: Назначения, на которые предложение намекает; пусто,
        когда ни одного не названо.
    """
    found = {
        kind
        for kind, keywords in DEVICE_KIND_WORDS.items()
        if any(mentions(text, (keyword,)) for keyword in keywords)
    }
    return frozenset(found)


def capability_in(text: str) -> Capability | None:
    """Возвращает способность, о которой просит предложение.

    Отрицающие слова выигрывают у положительных, потому что в «выключи свет»
    положительного глагола нет, а значит оно ровно противоположное «включи свет».

    Args:
        text: Приведённое предложение.

    Returns:
        Capability | None: Способность, о которой просят, или None, когда ни о какой.
    """
    for capability in (Capability.OFF, Capability.DEHUMIDIFY, Capability.HUMIDIFY):
        if mentions(text, CAPABILITY_WORDS[capability]):
            return capability
    for capability in (Capability.ON, Capability.COOL, Capability.HEAT):
        if mentions(text, CAPABILITY_WORDS[capability]):
            return capability
    return None


def duration_in(text: str) -> int | None:
    """Возвращает задержку, о которой просит предложение, в минутах.

    Args:
        text: Приведённое предложение.

    Returns:
        int | None: Задержка в минутах или None, когда предложения о задержке нет.
    """
    if not mentions(text, SCHEDULE_WORDS):
        return None
    for word in text.split():
        minutes = DURATION_WORDS.get(word)
        if minutes is not None:
            return minutes
    return None


def area_in(text: str) -> str | None:
    """Возвращает место, названное в предложении.

    Args:
        text: Приведённое предложение.

    Returns:
        str | None: Название места или None, когда места в предложении нет.
    """
    for word in text.split():
        if any(shares_prefix(word, keyword) for keyword in AREA_WORDS):
            return word
    return None


def switch_everything(text: str) -> bool:
    """Сообщает, обращено ли предложение ко всем устройствам дома.

    Args:
        text: Приведённое предложение.

    Returns:
        bool: True, когда предложение называет весь дом.
    """
    return mentions(text, EVERYTHING_WORDS)
