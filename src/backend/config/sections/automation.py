"""Периоды фоновых рабочих циклов."""

from __future__ import annotations

import os


def automation_cycle_sec() -> float:
    """Как часто запускается цикл автоматизации.

    Returns:
        float: Секунды между циклами.
    """
    return float(os.getenv("AUTOMATION_CYCLE_SEC", "10.0"))


def automation_scenario_tick_sec() -> float:
    """Как часто продвигаются сценарии.

    Returns:
        float: Секунды между шагами.
    """
    return float(os.getenv("AUTOMATION_SCENARIO_TICK_SEC", "5.0"))


def automation_manual_override_minutes() -> int:
    """Сколько ручная команда сдерживает автоматизацию.

    Returns:
        int: Минуты ручного приоритета.
    """
    return int(os.getenv("AUTOMATION_MANUAL_OVERRIDE_MINUTES", "30"))


def automation_summary_ttl_sec() -> int:
    """Кратчайший промежуток между двумя сводками автоматизации.

    Returns:
        int: Секунды между сообщениями.
    """
    return int(os.getenv("AUTOMATION_SUMMARY_TTL_SEC", "600"))


def automation_scenario_summary_ttl_sec() -> int:
    """Кратчайший промежуток между двумя сводками сценария.

    Returns:
        int: Секунды между сообщениями.
    """
    return int(os.getenv("AUTOMATION_SCENARIO_SUMMARY_TTL_SEC", "600"))
