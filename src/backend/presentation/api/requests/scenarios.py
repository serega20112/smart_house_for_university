"""Тело запроса сценария и перевод его в команду постановки."""

from __future__ import annotations

from pydantic import Field

from backend.application.dto.scenario.schedule_scenario_command import ScheduleScenarioCommand
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.presentation.api.base import StrictModel

DELAY_MAX_MINUTES = 10080
DURATION_MAX_MINUTES = 10080
TEMPERATURE_MIN = -50.0
TEMPERATURE_MAX = 80.0


class ScenarioCreateBody(StrictModel):
    """Запрос на отложенное действие.

    Attributes:
        capability: Способность, которую сценарий выполняет.
        delay_minutes: Сколько ждать до начала действия.
        target: Место или предмет, который назвал человек.
        target_temperature: Температура, к которой сценарий идёт, или None.
        completion_behavior: Что будет с устройствами после.
        duration_minutes: Сколько сценарию разрешено идти.
    """

    capability: Capability
    delay_minutes: int | None = Field(default=None, ge=0, le=DELAY_MAX_MINUTES)
    target: str | None = None
    target_temperature: float | None = Field(
        default=None, ge=TEMPERATURE_MIN, le=TEMPERATURE_MAX
    )
    completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION
    duration_minutes: int | None = Field(default=None, ge=1, le=DURATION_MAX_MINUTES)


def schedule_command(body: ScenarioCreateBody) -> ScheduleScenarioCommand:
    """Возвращает команду постановки сценария.

    Args:
        body: Отложенное действие, которое попросил человек.

    Returns:
        ScheduleScenarioCommand: Команда, понятная сценарию приложения.
    """
    return ScheduleScenarioCommand(
        action=ScenarioAction(
            capability=body.capability,
            target_temperature=(
                None if body.target_temperature is None else Temperature(body.target_temperature)
            ),
        ),
        delay_minutes=body.delay_minutes,
        target=body.target,
        completion_behavior=body.completion_behavior,
        duration_minutes=body.duration_minutes,
    )
