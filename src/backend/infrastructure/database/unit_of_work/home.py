"""Транзакция настройки дома.

Границы транзакций: одна сессия, одна транзакция, свои хранилища.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.interface.repositories.automation_repository import AutomationRepository
from backend.application.interface.repositories.dashboard_repository import DashboardRepository
from backend.application.interface.repositories.device_repository import DeviceRepository
from backend.application.interface.repositories.preferences_repository import PreferencesRepository
from backend.application.interface.repositories.scenario_repository import ScenarioRepository
from backend.application.interface.unit_of_work.home import HomeUnitOfWork, HomeUnitOfWorkFactory
from backend.infrastructure.database.repositories import (
    SqlAutomationRepository,
    SqlDashboardRepository,
    SqlDeviceRepository,
    SqlPreferencesRepository,
    SqlScenarioRepository,
)
from backend.infrastructure.database.unit_of_work.base import SqlUnitOfWork


class SqlHomeUnitOfWork(SqlUnitOfWork, HomeUnitOfWork):
    """Транзакция над конфигурацией одного дома.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    @property
    def devices(self) -> DeviceRepository:
        """Хранилище устройств нынешней транзакции."""
        return self.repository(SqlDeviceRepository)

    @property
    def automation(self) -> AutomationRepository:
        """Хранилище настройки автоматизации нынешней транзакции."""
        return self.repository(SqlAutomationRepository)

    @property
    def scenarios(self) -> ScenarioRepository:
        """Хранилище сценариев нынешней транзакции."""
        return self.repository(SqlScenarioRepository)

    @property
    def dashboard(self) -> DashboardRepository:
        """Хранилище раскладки экрана нынешней транзакции."""
        return self.repository(SqlDashboardRepository)

    @property
    def preferences(self) -> PreferencesRepository:
        """Хранилище настроек интерфейса нынешней транзакции."""
        return self.repository(SqlPreferencesRepository)


def make_home_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> HomeUnitOfWorkFactory:
    """Строит фабрику границ транзакции над домом.

    Args:
        session_factory: Фабрика сессий.

    Returns:
        HomeUnitOfWorkFactory: Вызываемый объект, дающий свежую границу.
    """

    def factory() -> SqlHomeUnitOfWork:
        """Создаёт новую границу над конфигурацией дома."""
        return SqlHomeUnitOfWork(session_factory)

    return factory
