"""SQL-репозитории: строки хранилища <-> агрегаты домена.

Каждый репозиторий живёт своим файлом рядом со своей таблицей; здесь собрано то,
что разрешает контейнер, и ничего больше. Общие приёмы — выборка одной строки,
пачка вставок, разбор уникального конфликта — лежат в `base`, дочерние строки,
читаемые вместе с родителем, — в `child_rows`.

Репозиторий никогда не делает commit и не откатывает транзакцию: ими владеет
граница работы.
"""

from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository
from backend.infrastructure.database.repositories.automation_repository import (
    SqlAutomationRepository,
)
from backend.infrastructure.database.repositories.board_network_repository import (
    SqlBoardNetworkRepository,
)
from backend.infrastructure.database.repositories.board_repository import SqlBoardRepository
from backend.infrastructure.database.repositories.claim_repository import SqlClaimRepository
from backend.infrastructure.database.repositories.dashboard_repository import (
    SqlDashboardRepository,
)
from backend.infrastructure.database.repositories.device_repository import SqlDeviceRepository
from backend.infrastructure.database.repositories.preferences_repository import (
    SqlPreferencesRepository,
)
from backend.infrastructure.database.repositories.scenario_repository import (
    SqlScenarioRepository,
)

__all__ = [
    "SqlAccountRepository",
    "SqlAutomationRepository",
    "SqlBoardNetworkRepository",
    "SqlBoardRepository",
    "SqlClaimRepository",
    "SqlDashboardRepository",
    "SqlDeviceRepository",
    "SqlPreferencesRepository",
    "SqlScenarioRepository",
]
