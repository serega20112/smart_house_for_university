"""Чтение стороны, границы транзакций и дешёвые выборки устройств."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from backend.application.interface.queries.account_queries import AccountQueries
from backend.application.interface.queries.automation_queries import AutomationQueries
from backend.application.interface.queries.board_queries import BoardQueries
from backend.application.interface.queries.device_queries import DeviceQueries
from backend.application.interface.queries.scenario_queries import ScenarioQueries
from backend.application.interface.services.home_device_directory import HomeDeviceDirectory
from backend.application.interface.unit_of_work.account import AccountUnitOfWorkFactory
from backend.application.interface.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.infrastructure.database.queries import (
    SqlAccountQueries,
    SqlAutomationQueries,
    SqlBoardQueries,
    SqlDeviceQueries,
    SqlHomeDeviceDirectory,
    SqlScenarioQueries,
)
from backend.infrastructure.database.unit_of_work import (
    make_account_unit_of_work,
    make_board_onboarding_unit_of_work,
    make_home_unit_of_work,
)

APP = Scope.APP


class PersistenceProvider(Provider):
    """Чтение стороны, границы транзакций и дешёвые чтения дома."""

    @provide(scope=APP)
    def account_queries(self, engine: AsyncEngine) -> AccountQueries:
        """Собирает чтения аккаунтов."""
        return SqlAccountQueries(engine)

    @provide(scope=APP)
    def device_queries(self, engine: AsyncEngine) -> DeviceQueries:
        """Собирает чтения настройки устройств."""
        return SqlDeviceQueries(engine)

    @provide(scope=APP)
    def automation_queries(self, engine: AsyncEngine) -> AutomationQueries:
        """Собирает чтения настройки автоматизации."""
        return SqlAutomationQueries(engine)

    @provide(scope=APP)
    def scenario_queries(self, engine: AsyncEngine) -> ScenarioQueries:
        """Собирает чтения сценариев."""
        return SqlScenarioQueries(engine)

    @provide(scope=APP)
    def board_queries(self, engine: AsyncEngine) -> BoardQueries:
        """Собирает чтения плат."""
        return SqlBoardQueries(engine)

    @provide(scope=APP)
    def account_uow(self, session_factory: async_sessionmaker) -> AccountUnitOfWorkFactory:
        """Собирает фабрику транзакций аккаунта."""
        return make_account_unit_of_work(session_factory)

    @provide(scope=APP)
    def home_uow(self, session_factory: async_sessionmaker) -> HomeUnitOfWorkFactory:
        """Собирает фабрику транзакций дома."""
        return make_home_unit_of_work(session_factory)

    @provide(scope=APP)
    def onboarding_uow(
        self, session_factory: async_sessionmaker
    ) -> BoardOnboardingUnitOfWorkFactory:
        """Собирает фабрику транзакций плат."""
        return make_board_onboarding_unit_of_work(session_factory)

    @provide(scope=APP)
    def home_directory(self, engine: AsyncEngine) -> HomeDeviceDirectory:
        """Собирает дешёвые чтения, которыми переводят сообщения платы."""
        return SqlHomeDeviceDirectory(engine)
