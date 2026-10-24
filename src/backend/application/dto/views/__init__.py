"""Модели чтения прикладного слоя: то, что показывает экран.

Проекции для чтения раньше жили в домене, из-за чего ядро узнавало форму интерфейса —
классический перевёрнутый CQRS. Здесь они и должны быть: домен оставляет `Device`,
`DeviceStatus`, `HomeState` — то, что имеет инварианты, а вид для экрана собирается тут.

Барель собран по той же причине, что и папки команд: вызывающий называет одну точку —
`application.dto.views`, — а не ворох несвязанных форм.
"""

from backend.application.dto.views.account_profile import AccountProfile
from backend.application.dto.views.auth_record import AuthRecord
from backend.application.dto.views.automation_view import AutomationView
from backend.application.dto.views.board_claim_view import BoardClaimView
from backend.application.dto.views.board_network_view import BoardNetworkView
from backend.application.dto.views.board_view import BoardView
from backend.application.dto.views.capability_report import CapabilityFailure, CapabilityReport
from backend.application.dto.views.dashboard_view import DashboardView
from backend.application.dto.views.device_view import DeviceView
from backend.application.dto.views.home_snapshot_view import HomeSnapshotView
from backend.application.dto.views.preferences_view import PreferencesView
from backend.application.dto.views.reading_view import ReadingView
from backend.application.dto.views.scenario_view import ScenarioView

__all__ = [
    "AccountProfile",
    "AuthRecord",
    "AutomationView",
    "BoardClaimView",
    "BoardNetworkView",
    "BoardView",
    "CapabilityFailure",
    "CapabilityReport",
    "DashboardView",
    "DeviceView",
    "HomeSnapshotView",
    "PreferencesView",
    "ReadingView",
    "ScenarioView",
]
