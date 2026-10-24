from __future__ import annotations

import pytest

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.services.language.lexicon import intent_in
from backend.application.services.language.lexicon_understanding import (
    DictionaryFirstUnderstanding,
    LexiconUnderstanding,
)
from backend.application.services.language.parser import SentenceParser
from backend.domain.value_objects.devices.capability import Capability

PARSER = SentenceParser()


class RecordedUnderstanding(CommandUnderstandingPort):
    """Запоминает, о чём её спрашивали, и отвечает заранее заготовленным пониманием."""

    def __init__(self, answer: CommandUnderstanding) -> None:
        self.answer = answer
        self.asked: list[str] = []

    async def understand(self, text: str) -> CommandUnderstanding:
        self.asked.append(text)
        return self.answer

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        return True


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("выключи всё", Intent.SWITCH_ALL),
        ("выключи все устройства", Intent.SWITCH_ALL),
        ("включи свет", Intent.SWITCH_DEVICE),
        ("погаси лампу", Intent.SWITCH_DEVICE),
        ("сделай прохладнее", Intent.RUN_CAPABILITY),
        ("тут жарко", Intent.RUN_CAPABILITY),
        ("какая температура?", Intent.READ_TEMPERATURE),
        ("сколько градусов в комнате", Intent.READ_TEMPERATURE),
        ("какая влажность", Intent.READ_HUMIDITY),
        ("сделай 20 градусов", Intent.SET_TEMPERATURE),
        ("поставь влажность 45 процентов", Intent.SET_HUMIDITY),
        ("через полчаса сделай 20 градусов", Intent.SCHEDULE_SCENARIO),
        ("отмени сценарий", Intent.CANCEL_SCENARIO),
        ("статус дома", Intent.DESCRIBE_HOME),
    ],
)
def test_the_dictionary_reads_the_name_of_the_intent(spoken: str, expected: Intent) -> None:
    facts = PARSER.parse(spoken)

    assert intent_in(spoken, facts) is expected


@pytest.mark.parametrize(
    "spoken",
    [
        "включи",
        "покрась стену",
        "нарисуй кота",
    ],
)
def test_the_dictionary_stays_quiet_about_what_it_does_not_know(spoken: str) -> None:
    facts = PARSER.parse(spoken)

    assert intent_in(spoken, facts) is None


async def test_the_dictionary_returns_the_parameters_it_read() -> None:
    understanding = await LexiconUnderstanding(parser=PARSER).understand("выключи всё")

    assert understanding.intent is Intent.SWITCH_ALL
    assert understanding.capability is Capability.OFF
    assert understanding.confidence == 1.0


async def test_the_dictionary_is_never_half_sure() -> None:
    pipeline = LexiconUnderstanding(parser=PARSER)

    known = await pipeline.understand("включи свет")
    unknown = await pipeline.understand("покрась стену")

    assert await pipeline.is_confident_enough(known) is True
    assert await pipeline.is_confident_enough(unknown) is False
    assert unknown.intent is None
    assert unknown.confidence == 0.0


async def test_a_known_phrase_never_reaches_the_semantic_pipeline() -> None:
    semantic = RecordedUnderstanding(CommandUnderstanding())
    pipeline = DictionaryFirstUnderstanding(
        dictionary=LexiconUnderstanding(parser=PARSER), semantic=semantic
    )

    understood = await pipeline.understand("выключи всё")

    assert understood.intent is Intent.SWITCH_ALL
    assert semantic.asked == []


async def test_an_unknown_phrase_falls_through_to_the_semantic_pipeline() -> None:
    answer = CommandUnderstanding(intent=Intent.DESCRIBE_HOME, confidence=0.9)
    semantic = RecordedUnderstanding(answer)
    pipeline = DictionaryFirstUnderstanding(
        dictionary=LexiconUnderstanding(parser=PARSER), semantic=semantic
    )

    understood = await pipeline.understand("душно тут у вас")

    assert understood is answer
    assert semantic.asked == ["душно тут у вас"]


async def test_the_combined_pipeline_does_not_let_an_unread_phrase_through() -> None:
    semantic = RecordedUnderstanding(CommandUnderstanding())
    pipeline = DictionaryFirstUnderstanding(
        dictionary=LexiconUnderstanding(parser=PARSER), semantic=semantic
    )

    understood = await pipeline.understand("покрась стену")

    assert await pipeline.is_confident_enough(understood) is False
