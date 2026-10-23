"""Порты хранилищ доменных объектов.

Интерфейс описывает работу с данными, а не способ её выполнения: SQL здесь только
в реализации. Базовые операции лежат в `base`, репозиторий фичи наследует ровно
нужный им набор.
"""

from backend.application.interface.repositories.account_repository import AccountRepository
from backend.application.interface.repositories.automation_repository import (
    AutomationRepository,
)
from backend.application.interface.repositories.base import (
    Creator,
    CrudRepository,
    Deleter,
    ListAll,
    Loader,
    Reader,
    Saver,
    Updater,
)
from backend.application.interface.repositories.board_repository import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from backend.application.interface.repositories.dashboard_repository import DashboardRepository
from backend.application.interface.repositories.device_repository import DeviceRepository
from backend.application.interface.repositories.preferences_repository import (
    PreferencesRepository,
)
from backend.application.interface.repositories.scenario_repository import ScenarioRepository

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
