"""Порты хранилищ доменных объектов.

Интерфейс описывает работу с данными, а не способ её выполнения: SQL здесь только
в реализации. Базовые операции лежат в `base`, репозиторий фичи наследует ровно
нужный им набор.
"""

from backend.application.interfaces.repositories.account_repository import AccountRepository
from backend.application.interfaces.repositories.automation_repository import (
    AutomationRepository,
)
from backend.application.interfaces.repositories.base import (
    Creator,
    CrudRepository,
    Deleter,
    ListAll,
    Loader,
    Reader,
    Saver,
    Updater,
)
from backend.application.interfaces.repositories.board_repository import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from backend.application.interfaces.repositories.dashboard_repository import DashboardRepository
from backend.application.interfaces.repositories.device_repository import DeviceRepository
from backend.application.interfaces.repositories.preferences_repository import (
    PreferencesRepository,
)
from backend.application.interfaces.repositories.scenario_repository import ScenarioRepository

__all__ = [
    "AccountRepository",
    "AutomationRepository",
    "BoardNetworkRepository",
    "BoardRepository",
    "ClaimRepository",
    "Creator",
    "CrudRepository",
    "DashboardRepository",
    "Deleter",
    "DeviceRepository",
    "ListAll",
    "Loader",
    "PreferencesRepository",
    "Reader",
    "Saver",
    "ScenarioRepository",
    "Updater",
]
