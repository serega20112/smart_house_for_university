"""Transaction boundary of a home.

Everything a user configured about their own house lives in one transaction: the
devices, the automation, the scenarios and the personalized projection. The
boundary exists because those aggregates are changed together, for example when an
account is provisioned.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from backend.application.ports.repositories.automation import AutomationRepository
from backend.application.ports.repositories.devices import DeviceRepository
from backend.application.ports.repositories.personalization import (
    DashboardRepository,
    PreferencesRepository,
)
from backend.application.ports.repositories.scenarios import ScenarioRepository
from backend.application.ports.unit_of_work.transaction import TransactionalUnitOfWork


class HomeUnitOfWork(TransactionalUnitOfWork):
    """Transaction over the configuration of one home."""

    @property
    @abstractmethod
    def devices(self) -> DeviceRepository:
        """Return the device repository bound to the current transaction.

        Returns:
            DeviceRepository: Device repository.
        """

    @property
    @abstractmethod
    def automation(self) -> AutomationRepository:
        """Return the automation repository bound to the current transaction.

        Returns:
            AutomationRepository: Automation repository.
        """

    @property
    @abstractmethod
    def scenarios(self) -> ScenarioRepository:
        """Return the scenario repository bound to the current transaction.

        Returns:
            ScenarioRepository: Scenario repository.
        """

    @property
    @abstractmethod
    def dashboard(self) -> DashboardRepository:
        """Return the dashboard repository bound to the current transaction.

        Returns:
            DashboardRepository: Dashboard repository.
        """

    @property
    @abstractmethod
    def preferences(self) -> PreferencesRepository:
        """Return the preferences repository bound to the current transaction.

        Returns:
            PreferencesRepository: Preferences repository.
        """


class HomeUnitOfWorkFactory(Protocol):
    """Produces a fresh unit of work over the configuration of a home."""

    def __call__(self) -> HomeUnitOfWork:
        """Create a new unit of work.

        Returns:
            HomeUnitOfWork: New unit of work.
        """
