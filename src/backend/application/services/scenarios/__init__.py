"""Службы сценариев: отложенные обещания дома живут здесь.

Фоновый шаг, сворачивание stopped-сценария и общие для них мелочи разнесены по
модулям: каждый знает ровно одну вещь, а не весь жизненный цикл сразу.
"""

from backend.application.services.scenarios.advancing import ScenarioAdvancer
from backend.application.services.scenarios.details import (
    EXPECTED_REFUSALS,
    reason_of,
    restorable_states,
    scenario_payload,
    scenario_view,
)
from backend.application.services.scenarios.settling import ScenarioSettler

__all__ = [
    "EXPECTED_REFUSALS",
    "ScenarioAdvancer",
    "ScenarioSettler",
    "reason_of",
    "restorable_states",
    "scenario_payload",
    "scenario_view",
]
