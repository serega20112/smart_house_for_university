"""Tests of the intent classifier."""

from __future__ import annotations

import pytest

from smart_home_backend.domain.enums.intent import Intent
from smart_home_backend.infrastructure.nlp.classifier import EmbeddingIntentClassifier
from smart_home_backend.infrastructure.nlp.embedder import LexicalHashEmbedder
from smart_home_backend.infrastructure.nlp.references import INTENT_REFERENCES, reference_pairs


@pytest.fixture(scope="module")
def classifier() -> EmbeddingIntentClassifier:
    return EmbeddingIntentClassifier(LexicalHashEmbedder())


def test_every_intent_has_reference_phrases() -> None:
    for intent, phrases in INTENT_REFERENCES.items():
        assert phrases, f"{intent} has no reference phrase"


def test_reference_phrases_are_flattened() -> None:
    expected = sum(len(phrases) for phrases in INTENT_REFERENCES.values())
    assert len(reference_pairs()) == expected


async def test_light_command_is_recognized(classifier: EmbeddingIntentClassifier) -> None:
    prediction = await classifier.classify("включи свет")
    assert prediction.intent in (Intent.TURN_ON.value, Intent.TURN_ON_ALL.value)


async def test_cancel_command_is_recognized(classifier: EmbeddingIntentClassifier) -> None:
    prediction = await classifier.classify("отмени сценарий")
    assert prediction.intent == Intent.CANCEL_SCENARIO.value


async def test_confidence_is_normalized(classifier: EmbeddingIntentClassifier) -> None:
    prediction = await classifier.classify("выключи кондиционер")
    assert 0.0 <= prediction.confidence <= 1.0


async def test_empty_index_reports_unknown() -> None:
    empty = EmbeddingIntentClassifier(LexicalHashEmbedder(), references=[])
    prediction = await empty.classify("что угодно")
    assert prediction.intent == "UNKNOWN"
    assert prediction.confidence == 0.0
