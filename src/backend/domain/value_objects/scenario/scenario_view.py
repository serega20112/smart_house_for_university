"""Сценарий в том виде, в каком его показывает экран."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import ScenarioId
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus


@dataclass(frozen=True, slots=True)
class ScenarioView:
    """Описание одного сценария для интерфейса.

    Attributes:
        id: Идентификатор сценария.
        status: Этап, на котором находится сценарий.
        created_at: Момент, когда сценарий сохранили.
        start_at: Момент, когда сценарий начинает действовать.
        duration_minutes: Сколько ему разрешено идти, или None если без предела.
        target: Место или предмет, который назвал человек.
        completion_behavior: Что будет с устройствами после завершения.
        actions: Действия, которые сценарий выполняет.
    """

    id: ScenarioId
    status: ScenarioStatus
    created_at: datetime
    start_at: datetime
    duration_minutes: int | None
    target: str | None
    completion_behavior: CompletionBehavior
    actions: tuple[ScenarioAction, ...]
