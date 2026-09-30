"""Reference phrases used to classify user intents.

Each intent is described by several everyday formulations. A command is embedded
and matched against these references, so the system understands many ways of
saying the same thing without enumerating them by hand.
"""

from __future__ import annotations

from typing import Final

from smart_home_backend.domain.enums.intent import Intent

INTENT_REFERENCES: Final[dict[Intent, tuple[str, ...]]] = {
    Intent.TURN_ON: (
        "включи свет",
        "зажги лампу",
        "включи кондиционер",
        "запусти вентилятор",
        "включи увлажнитель",
        "дай свет",
        "врубай свет",
    ),
    Intent.TURN_OFF: (
        "выключи свет",
        "потуши свет",
        "выключи кондиционер",
        "останови вентилятор",
        "выключи лампу",
        "погаси свет",
        "выключи увлажнитель",
    ),
    Intent.TURN_OFF_ALL: (
        "выключи всё",
        "потуши всё",
        "вырубай все устройства",
        "полностью выключи свет",
        "обесточь всё",
    ),
    Intent.TURN_ON_ALL: (
        "включи всё",
        "зажги всё",
        "включи все устройства",
        "врубай всё",
    ),
    Intent.SET_TEMPERATURE: (
        "сделай 20 градусов",
        "поставь температуру 22",
        "установи 24 градуса",
        "температура 21",
        "сделай 25 градусов в комнате",
        "нагрей до 23",
    ),
    Intent.SET_HUMIDITY: (
        "сделай влажность 45 процентов",
        "поставь влажность 50",
        "увлажни комнату до 55",
        "влажность 40 процентов",
    ),
    Intent.COOL: (
        "тут жарко",
        "сделай прохладнее",
        "охлади комнату",
        "понизь температуру",
        "что-то жарковато",
        "станет посвежее",
        "слишком тепло",
    ),
    Intent.HEAT: (
        "тут холодно",
        "подними температуру",
        "сделай теплее",
        "погреть комнату",
        "замёрз",
        "прохладно стало",
    ),
    Intent.GET_STATUS: (
        "какое состояние",
        "статус дома",
        "что сейчас включено",
        "как обстановка",
        "покажи состояние",
    ),
    Intent.GET_TEMPERATURE: (
        "какая температура",
        "сколько градусов",
        "температура в комнате",
        "на сколько тепло",
    ),
    Intent.GET_HUMIDITY: (
        "какая влажность",
        "сколько процентов влажность",
        "влажность в комнате",
        "сухо или мокро",
    ),
    Intent.CREATE_SCENARIO: (
        "охлади комнату до 20 градусов я через полчаса приеду",
        "через час сделай 22 градуса",
        "поставь таймер на 20 градусов через 30 минут",
        "согрей комнату к моему возвращению через час",
        "через полчаса сделай прохладно",
    ),
    Intent.CANCEL_SCENARIO: (
        "отмени сценарий",
        "убери таймер",
        "отмени задачу",
        "анлируй сценарий",
        "прекрати сценарий",
    ),
}


def reference_pairs() -> list[tuple[str, str]]:
    """Return the reference phrases flattened into intent and phrase pairs.

    Returns:
        list[tuple[str, str]]: Intent names paired with their phrases.
    """
    return [
        (intent.value, phrase)
        for intent, phrases in INTENT_REFERENCES.items()
        for phrase in phrases
    ]
