"""Intent confidence policy."""

from __future__ import annotations

from smart_home_backend.domain.enums.intent import Intent
from smart_home_backend.domain.enums.operation import ClarificationReason


def clarification_reason(
    intent: Intent | None, confidence: float, threshold: float
) -> ClarificationReason | None:
    """Return why a command cannot be executed yet.

    Read only intents may answer with a guess, while state changing intents have
    to clear the confidence threshold, otherwise the system asks the user to
    rephrase instead of touching a device.

    Args:
        intent: Predicted intent or None when nothing was recognized.
        confidence: Similarity of the closest reference phrase.
        threshold: Similarity required to act without clarification.

    Returns:
        ClarificationReason | None: Reason to ask the user, or None when the
        command may proceed.
    """
    if intent is None:
        return ClarificationReason.UNRECOGNIZED_INTENT
    if intent.changes_device_state and confidence < threshold:
        return ClarificationReason.LOW_CONFIDENCE
    return None


def is_confident(intent: Intent | None, confidence: float, threshold: float) -> bool:
    """Return whether a command may be executed.

    Args:
        intent: Predicted intent or None when nothing was recognized.
        confidence: Similarity of the closest reference phrase.
        threshold: Similarity required to act without clarification.

    Returns:
        bool: True when the command may proceed.
    """
    return clarification_reason(intent, confidence, threshold) is None
