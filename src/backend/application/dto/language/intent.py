"""Что человек попросил сделать.

Здесь только сами намерения и перечень тех, что меняют дом, — и то и другое данные.
Разбор строки в намерение делает конвейер понимания, а не этот модуль.
"""

from __future__ import annotations

from enum import StrEnum


class Intent(StrEnum):
    """Набор действий, которые человек может назвать.

    Словарь принадлежит шине команд, а не модели: вот что человек вправе сказать,
    а как именно он это сформулирует — дело конвейера понимания.
    """

    SWITCH_DEVICE = "SWITCH_DEVICE"
    SWITCH_ALL = "SWITCH_ALL"
    SET_TEMPERATURE = "SET_TEMPERATURE"
    SET_HUMIDITY = "SET_HUMIDITY"
    RUN_CAPABILITY = "RUN_CAPABILITY"
    DESCRIBE_HOME = "DESCRIBE_HOME"
    READ_TEMPERATURE = "READ_TEMPERATURE"
    READ_HUMIDITY = "READ_HUMIDITY"
    SCHEDULE_SCENARIO = "SCHEDULE_SCENARIO"
    CANCEL_SCENARIO = "CANCEL_SCENARIO"


HOME_CHANGING_INTENTS: frozenset[Intent] = frozenset(
    {
        Intent.SWITCH_DEVICE,
        Intent.SWITCH_ALL,
        Intent.SET_TEMPERATURE,
        Intent.SET_HUMIDITY,
        Intent.RUN_CAPABILITY,
        Intent.SCHEDULE_SCENARIO,
        Intent.CANCEL_SCENARIO,
    }
)
