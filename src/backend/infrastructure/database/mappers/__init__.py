"""Мапперы: строки хранилища <-> объекты домена.

Правило переворота читается целиком в одном месте, а не размазано по репозиториям,
и ни один из них не начинает пахнуть SQL. Общий разбор значения в колонку живёт в
`base`, остальное разложено по фичам; здесь собрано, чтобы вызывающий написал одну
точку — `mappers`.
"""

from backend.infrastructure.database.mappers.accounts import user_from_row, user_to_row
from backend.infrastructure.database.mappers.automation import (
    automation_from_row,
    automation_to_row,
    participant_rows,
)
from backend.infrastructure.database.mappers.base import as_utc, parse_uuid, row_values
from backend.infrastructure.database.mappers.boards import (
    board_from_row,
    board_to_row,
    claim_from_row,
    claim_to_row,
    network_from_row,
    network_to_row,
)
from backend.infrastructure.database.mappers.dashboard import (
    dashboard_from_row,
    dashboard_to_row,
    widget_from_row,
    widget_rows,
)
from backend.infrastructure.database.mappers.device import (
    capability_rows,
    device_from_row,
    device_to_row,
)
from backend.infrastructure.database.mappers.preferences import (
    preferences_from_row,
    preferences_to_row,
)
from backend.infrastructure.database.mappers.scenario import (
    action_from_row,
    action_rows,
    captured_status_from_row,
    captured_status_rows,
    scenario_from_row,
    scenario_to_row,
)

__all__ = [
    "action_from_row",
    "action_rows",
    "as_utc",
    "automation_from_row",
    "automation_to_row",
    "board_from_row",
    "board_to_row",
    "capability_rows",
    "captured_status_from_row",
    "captured_status_rows",
    "claim_from_row",
    "claim_to_row",
    "dashboard_from_row",
    "dashboard_to_row",
    "device_from_row",
    "device_to_row",
    "network_from_row",
    "network_to_row",
    "parse_uuid",
    "participant_rows",
    "preferences_from_row",
    "preferences_to_row",
    "row_values",
    "scenario_from_row",
    "scenario_to_row",
    "user_from_row",
    "user_to_row",
    "widget_from_row",
    "widget_rows",
]
