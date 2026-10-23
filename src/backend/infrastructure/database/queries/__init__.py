"""Чтения стороны выбора: каждое — один вопрос и один читаемый образ."""

from __future__ import annotations

from backend.infrastructure.database.queries.accounts import SqlAccountQueries
from backend.infrastructure.database.queries.automation import (
    SqlAutomationQueries,
    automation_view_of,
)
from backend.infrastructure.database.queries.boards import (
    SqlBoardQueries,
    board_view_of,
    claim_view_of,
)
from backend.infrastructure.database.queries.devices import SqlDeviceQueries, device_view_of
from backend.infrastructure.database.queries.scenarios import (
    HOLDING_STAGES,
    SqlScenarioQueries,
    captured_statuses_of,
    scenario_actions_of,
    scenario_view_of,
)

__all__ = [
    "HOLDING_STAGES",
    "SqlAccountQueries",
    "SqlAutomationQueries",
    "SqlBoardQueries",
    "SqlDeviceQueries",
    "SqlScenarioQueries",
    "automation_view_of",
    "board_view_of",
    "captured_statuses_of",
    "claim_view_of",
    "device_view_of",
    "scenario_actions_of",
    "scenario_view_of",
]
