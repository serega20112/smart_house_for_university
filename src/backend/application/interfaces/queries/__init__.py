"""Порты чтений: срезы данных, подогнанные под экран.

Читающая сторона не открывает транзакции и отдаёт модели чтения из
`domain/value_objects`, поэтому ни хранилище, ни интерфейс не решают, как выглядит
строка для показа.
"""

from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.interfaces.queries.automation_queries import AutomationQueries
from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.queries.device_queries import DeviceQueries
from backend.application.interfaces.queries.scenario_queries import ScenarioQueries

__all__ = [
    "AccountQueries",
    "AutomationQueries",
    "BoardQueries",
    "DeviceQueries",
    "ScenarioQueries",
]
