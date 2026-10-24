"""
Источник команды, от самого важного к самому простому.

Приоритетов четыре, и правило «кто кого перебивает» читается из порядка членов:
авария сильнее сценария, сценарий сильнее автоматики, автоматика сильнее ручного
хода.
"""

from __future__ import annotations

from enum import StrEnum


class ControlSource(StrEnum):
    """Источник команды, от самого важного к самому простому."""

    EMERGENCY = "EMERGENCY"
    SCENARIO = "SCENARIO"
    AUTOMATION = "AUTOMATION"
    MANUAL = "MANUAL"
