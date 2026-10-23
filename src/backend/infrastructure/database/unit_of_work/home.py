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
    """Transaction over the configuration of one home.

    Args:
        session_factory: Factory producing the session of the block.

    Returns:
        None.
    """

    @property
    def devices(self) -> DeviceRepository:
        """Return the device repository bound to the current transaction.

        Returns:
            DeviceRepository: Device repository.
        """
        return self.repository(SqlDeviceRepository)

    @property
    def automation(self) -> AutomationRepository:
        """Return the automation repository bound to the current transaction.

        Returns:
            AutomationRepository: Automation repository.
        """
        return self.repository(SqlAutomationRepository)

    @property
    def scenarios(self) -> ScenarioRepository:
        """Return the scenario repository bound to the current transaction.

        Returns:
            ScenarioRepository: Scenario repository.
        """
        return self.repository(SqlScenarioRepository)

    @property
    def dashboard(self) -> DashboardRepository:
        """Return the dashboard repository bound to the current transaction.

        Returns:
            DashboardRepository: Dashboard repository.
        """
        return self.repository(SqlDashboardRepository)

    @property
    def preferences(self) -> PreferencesRepository:
        """Return the preferences repository bound to the current transaction.

        Returns:
            PreferencesRepository: Preferences repository.
        """
        return self.repository(SqlPreferencesRepository)


def make_home_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> HomeUnitOfWorkFactory:
    """Build the factory producing units of work over a home.

    Args:
        session_factory: Factory producing sessions.

    Returns:
        HomeUnitOfWorkFactory: Callable handing out a fresh unit of work.
    """

    def factory() -> SqlHomeUnitOfWork:
        """Create a new unit of work over the configuration of a home.

        Returns:
            SqlHomeUnitOfWork: Unit of work bound to its own session.
        """
        return SqlHomeUnitOfWork(session_factory)

    return factory
