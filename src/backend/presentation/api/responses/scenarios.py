"""Ответы про сценарии."""

from __future__ import annotations

from datetime import datetime

from backend.application.dto.views.scenario_view import ScenarioView
from backend.presentation.api.responses.common import StrictModel


class ScenarioActionResponse(StrictModel):
    """Одно действие сценария.

    Attributes:
        capability: Способность, которую действие выполняет.
        target_temperature: Температура, к которой действие идёт, или None.
    """

    capability: str
    target_temperature: float | None


class ScenarioResponse(StrictModel):
    """Один сценарий таким, каким его видит интерфейс.

    Attributes:
        id: Идентификатор сценария.
        status: Этап, на котором сценарий находится.
        created_at: Момент, когда сценарий сохранили.
        start_at: Момент, когда сценарий начинает действовать.
        duration_minutes: Сколько ему разрешено идти, или None без границы.
        target: Место или предмет, который назвал человек.
        completion_behavior: Что будет с устройствами после.
        actions: Действия, которые сценарий выполняет.
    """

    id: str
    status: str
    created_at: datetime
    start_at: datetime
    duration_minutes: int | None
    target: str | None
    completion_behavior: str
    actions: list[ScenarioActionResponse]


def scenario_of(scenario: ScenarioView) -> ScenarioResponse:
    """Возвращает тело сценария.

    Args:
        scenario: Сценарий таким, каким его видит прикладной слой.

    Returns:
        ScenarioResponse: Тело сценария.
    """
    return ScenarioResponse(
        id=str(scenario.id),
        status=scenario.status.value,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior.value,
        actions=[
            ScenarioActionResponse(
                capability=action.capability.value,
                target_temperature=(
                    None if action.target_temperature is None else action.target_temperature.celsius
                ),
            )
            for action in scenario.actions
        ],
    )
