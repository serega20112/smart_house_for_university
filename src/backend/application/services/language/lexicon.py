"""Намерение, узнанное словарём, без единого вектора.

Вектор нужен там, где слова не совпадают: «душно» и «жарко» близки по смыслу, но не по
буквам. Там же, где человек говорит теми словами, которые словарь уже знает, ближайший
сосед ничего не добавляет, зато стоит кодирования на каждом запросе и загрузки модели в
каждый процесс. Поэтому знакомые слова толкует этот модуль, а смысловой конвейер
спрашивают только о том, что осталось непонятым.

Правила идут от самого узкого признака к самому общему: задержка, отмена, вопрос о
показаниях, названное число, названная способность. Так «через полчаса сделай 20
градусов» остаётся сценарием, а не сменой цели, хотя число в нём есть.
"""

from __future__ import annotations

from typing import Final

from backend.application.dto.language.intent import Intent
from backend.application.services.language import vocabulary
from backend.application.services.language.parser import SentenceFacts, normalize
from backend.domain.value_objects.devices.capability import Capability

SWITCHING: Final[tuple[Capability, ...]] = (Capability.ON, Capability.OFF)


def intent_in(text: str, facts: SentenceFacts) -> Intent | None:
    """Возвращает намерение, которое словарь узнаёт в предложении.

    Args:
        text: Предложение в сыром виде, каким его получил интерфейс.
        facts: То, что читатель параметров уже вынул из этого предложения.

    Returns:
        Intent | None: Узнанное намерение или None, когда словарь не узнал ничего и
        решать остаётся смысловому конвейеру.
    """
    spoken = normalize(text)
    if facts.delay_minutes is not None and vocabulary.mentions(spoken, vocabulary.SCHEDULE_WORDS):
        return Intent.SCHEDULE_SCENARIO
    if vocabulary.mentions(spoken, vocabulary.CANCEL_WORDS):
        return Intent.CANCEL_SCENARIO
    if vocabulary.mentions(spoken, vocabulary.DESCRIBE_WORDS):
        return Intent.DESCRIBE_HOME
    if _asks(spoken, vocabulary.TEMPERATURE_QUESTIONS):
        return Intent.READ_TEMPERATURE
    if _asks(spoken, vocabulary.HUMIDITY_QUESTIONS):
        return Intent.READ_HUMIDITY
    if facts.temperature is not None:
        return Intent.SET_TEMPERATURE
    if facts.humidity is not None:
        return Intent.SET_HUMIDITY
    if facts.capability in SWITCHING:
        return _switching_intent(spoken, facts)
    if facts.capability is not None:
        return Intent.RUN_CAPABILITY
    return None


def _asks(spoken: str, questions: tuple[str, ...]) -> bool:
    """Сообщает, просят ли в предложении показания.

    Вопрос сравнивается целиком: оборота «какая» достаточно, чтобы узнать просьбу о
    температуре, но недостаточно, чтобы понять, о чём именно спрашивают, поэтому слова
    вопроса берут вместе, а не поодиночке.

    Args:
        spoken: Приведённое предложение.
        questions: Обороты, которыми спрашивают о показании.

    Returns:
        bool: True, когда в предложении есть целый вопросительный оборот.
    """
    return any(question in spoken for question in questions)


def _switching_intent(spoken: str, facts: SentenceFacts) -> Intent | None:
    """Уточняет, что именно включают или выключают.

    Включить, не назвав что, нельзя: «включи» само по себе не говорит, чему менять
    положение, поэтому намерения нет и интерфейс спросит заново.

    Args:
        spoken: Приведённое предложение.
        facts: Прочитанные из него параметры.

    Returns:
        Intent | None: Весь дом, одно устройство или ничего.
    """
    if vocabulary.switch_everything(spoken):
        return Intent.SWITCH_ALL
    if facts.device_kinds or facts.device_name is not None:
        return Intent.SWITCH_DEVICE
    return None
