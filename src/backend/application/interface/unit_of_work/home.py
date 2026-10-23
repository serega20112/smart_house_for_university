"""Граница транзакции дома.

Всё, что человек настроил в собственном доме, живёт в одной транзакции: устройства,
автоматизация, сценарии и персональная проекция. Граница существует потому, что эти
агрегаты меняются вместе — например когда аккаунту обустраивают дом.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from backend.application.interface.repositories.automation_repository import (
    AutomationRepository,
)
from backend.application.interface.repositories.dashboard_repository import DashboardRepository
from backend.application.interface.repositories.device_repository import DeviceRepository
from backend.application.interface.repositories.preferences_repository import (
    PreferencesRepository,
)
from backend.application.interface.repositories.scenario_repository import ScenarioRepository
from backend.application.interface.unit_of_work.transaction import TransactionalUnitOfWork


class HomeUnitOfWork(TransactionalUnitOfWork):
    """Транзакция над конфигурацией одного дома."""

    @property
    @abstractmethod
    def devices(self) -> DeviceRepository:
        """Репозиторий устройств текущей транзакции."""

    @property
    @abstractmethod
    def automation(self) -> AutomationRepository:
        """Репозиторий настроек автоматизации текущей транзакции."""

    @property
    @abstractmethod
    def scenarios(self) -> ScenarioRepository:
        """Репозиторий сценариев текущей транзакции."""

    @property
    @abstractmethod
    def dashboard(self) -> DashboardRepository:
        """Репозиторий раскладки панели текущей транзакции."""

    @property
    @abstractmethod
    def preferences(self) -> PreferencesRepository:
        """Репозиторий настроек интерфейса текущей транзакции."""


class HomeUnitOfWorkFactory(Protocol):
    """Создаёт свежую границу транзакции дома."""

    def __call__(self) -> HomeUnitOfWork:
        """Возвращает новую границу."""
