"""Tests of the intent confidence policy."""

from __future__ import annotations

from smart_home_backend.domain.enums.intent import Intent
from smart_home_backend.domain.enums.operation import ClarificationReason
from smart_home_backend.domain.policies import clarification_reason, is_confident


def test_unknown_intent_asks_for_clarification() -> None:
    assert clarification_reason(None, 0.9, 0.5) is ClarificationReason.UNRECOGNIZED_INTENT


def test_low_confidence_action_asks_for_clarification() -> None:
    reason = clarification_reason(Intent.TURN_ON, 0.2, 0.5)
    assert reason is ClarificationReason.LOW_CONFIDENCE


def test_confident_action_is_executable() -> None:
    assert clarification_reason(Intent.TURN_ON, 0.8, 0.5) is None


def test_read_intent_never_requires_clarification() -> None:
    assert clarification_reason(Intent.GET_STATUS, 0.05, 0.5) is None
    assert is_confident(Intent.GET_TEMPERATURE, 0.0, 0.5) is True
