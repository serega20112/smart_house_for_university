"""Отложенное действие, о котором попросил человек."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.entities.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior


@dataclass(frozen=True, slots=True)
class ScheduleScenarioCommand:
    """Значения запроса поставить сценарий.

    Attributes:
        action: Единственное действие, которое сценарий выполняет.
        delay_minutes: Сколько ждать до действия.
        target: Место или предмет, который назвал человек.
        completion_behavior: Что будет с устройствами после.
        duration_minutes: Сколько сценарию разрешено идти.
    """

    action: ScenarioAction
    delay_minutes: int | None = None
    target: str | None = None
    completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION
    duration_minutes: int | None = None
