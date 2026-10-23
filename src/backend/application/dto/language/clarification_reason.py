"""Почему команду нельзя выполнить как есть."""

from __future__ import annotations

from enum import StrEnum


class ClarificationReason(StrEnum):
    """Причина, по которой команде чего-то не хватает."""

    UNRECOGNIZED_INTENT = "UNRECOGNIZED_INTENT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN_DEVICE = "UNKNOWN_DEVICE"
    MISSING_TEMPERATURE = "MISSING_TEMPERATURE"
    MISSING_HUMIDITY = "MISSING_HUMIDITY"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
