"""Персонализация: настройки интерфейса и раскладка главного экрана."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.use_cases.personalization.read_dashboard import ReadDashboardUseCase
from backend.application.use_cases.personalization.read_preferences import ReadPreferencesUseCase
from backend.application.use_cases.personalization.update_dashboard import UpdateDashboardUseCase
from backend.application.use_cases.personalization.update_preferences import (
    UpdatePreferencesUseCase,
)

REQUEST = Scope.REQUEST


class PersonalizationProvider(Provider):
    """Всё, что интерфейс настраивает в собственной проекции дома."""

    @provide(scope=REQUEST)
    def read_preferences(self, home_uow: HomeUnitOfWorkFactory) -> ReadPreferencesUseCase:
        """Собирает чтение настроек интерфейса."""
        return ReadPreferencesUseCase(home_uow)

    @provide(scope=REQUEST)
    def update_preferences(self, home_uow: HomeUnitOfWorkFactory) -> UpdatePreferencesUseCase:
        """Собирает изменение настроек интерфейса."""
        return UpdatePreferencesUseCase(home_uow)

    @provide(scope=REQUEST)
    def read_dashboard(self, home_uow: HomeUnitOfWorkFactory) -> ReadDashboardUseCase:
        """Собирает чтение раскладки экрана."""
        return ReadDashboardUseCase(home_uow)

    @provide(scope=REQUEST)
    def update_dashboard(self, home_uow: HomeUnitOfWorkFactory) -> UpdateDashboardUseCase:
        """Собирает замену раскладки экрана."""
        return UpdateDashboardUseCase(home_uow)
