"""Границы транзакций PostgreSQL: одна сессия, одна транзакция, свои хранилища.

Модуль живёт в корне инфраструктуры, а не в пакете: это один слой plumbing над
движком, и выбирать границу транзакции вызывающему не из чего — их ровно три, по
одной на жизнь: аккаунты, настройка дома и сопряжение плат.

Хранилища граница держит в кеше: два обращения внутри одной транзакции должны
видеть одни и те же объекты, а не два независимых чтения одного состояния.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction, async_sessionmaker

from backend.application.interfaces.repositories.account_repository import AccountRepository
from backend.application.interfaces.repositories.automation_repository import AutomationRepository
from backend.application.interfaces.repositories.board_repository import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from backend.application.interfaces.repositories.dashboard_repository import DashboardRepository
from backend.application.interfaces.repositories.device_repository import DeviceRepository
from backend.application.interfaces.repositories.preferences_repository import PreferencesRepository
from backend.application.interfaces.repositories.scenario_repository import ScenarioRepository
from backend.application.interfaces.unit_of_work.account import (
    AccountUnitOfWork,
    AccountUnitOfWorkFactory,
)
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWork,
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWork, HomeUnitOfWorkFactory
from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository
from backend.infrastructure.database.repositories.automation_repository import (
    SqlAutomationRepository,
)
from backend.infrastructure.database.repositories.board_network_repository import (
    SqlBoardNetworkRepository,
)
from backend.infrastructure.database.repositories.board_repository import SqlBoardRepository
from backend.infrastructure.database.repositories.claim_repository import SqlClaimRepository
from backend.infrastructure.database.repositories.dashboard_repository import SqlDashboardRepository
from backend.infrastructure.database.repositories.device_repository import SqlDeviceRepository
from backend.infrastructure.database.repositories.preferences_repository import (
    SqlPreferencesRepository,
)
from backend.infrastructure.database.repositories.scenario_repository import SqlScenarioRepository


class SessionBound(Protocol):
    """Хранилище, принимающее сессию транзакции.

    Attributes:
        session: Сессия, которую открыла граница транзакции.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище сессией текущей транзакции.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """


class SqlUnitOfWork:
    """Одна сессия, одна транзакция и привязанные к ним хранилища.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует границу транзакции.

        Args:
            session_factory: Фабрика сессий.
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._transaction: AsyncSessionTransaction | None = None
        self._repositories: dict[type[SessionBound], SessionBound] = {}

    async def __aenter__(self) -> Self:
        """Открывает сессию и транзакцию блока.

        Returns:
            Self: Граница, годная к употреблению внутри блока.
        """
        self._session = self._session_factory()
        self._transaction = await self._session.begin()
        self._repositories.clear()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Откатывает при ошибке и отпускает сессию, но не коммитит молча.

        Сохраняет только `commit()`, вызванный внутри блока; без него изменения не
        фиксируются, а чистый выход лишь закрывает сессию (незакоммиченная транзакция
        при закрытии откатится сама). При ошибке — явный откат. Соединение возвращает
        в пул закрытие сессии.

        Args:
            exc_type: Тип поднятого исключения или None.
            exc_val: Само исключение или None.
            exc_tb: Его traceback или None.
        """
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None
            self._transaction = None
            self._repositories.clear()

    async def commit(self) -> None:
        """Атомарно сохраняет всё сделанное внутри блока."""
        if self._transaction is not None:
            await self._transaction.commit()

    async def rollback(self) -> None:
        """Отменяет всё сделанное внутри блока."""
        if self._transaction is not None:
            await self._transaction.rollback()

    @property
    def session(self) -> AsyncSession:
        """Возвращает сессию текущей транзакции.

        Returns:
            AsyncSession: Сессия открытого блока.

        Raises:
            RuntimeError: Когда границу используют вне её блока.
        """
        if self._session is None:
            raise RuntimeError("the unit of work is used outside of its block")
        return self._session

    def repository[Bound: SessionBound](self, model: type[Bound]) -> Bound:
        """Возвращает единственный экземпляр хранилища, который даёт эта граница.

        Кеш хранит разнородные хранилища под общим типом, поэтому попадание в кеш
        проверяется `isinstance`: это и сужает тип до запрашиваемого хранилища, и
        честно защищает от случая, когда под ключом лежит не то, что просят.

        Args:
            model: Класс хранилища, который надо вернуть.

        Returns:
            Bound: Хранилище, привязанное к сессии текущей транзакции.

        Raises:
            RuntimeError: Когда границу используют вне её блока.
        """
        cached = self._repositories.get(model)
        if isinstance(cached, model):
            return cached
        if self._session is None:
            raise RuntimeError("the unit of work is used outside of its block")
        created = model(self._session)
        self._repositories[model] = created
        return created


class SqlAccountUnitOfWork(SqlUnitOfWork, AccountUnitOfWork):
    """Транзакция над аккаунтами и больше ни над чем.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    @property
    def accounts(self) -> AccountRepository:
        """Хранилище аккаунтов нынешней транзакции."""
        return self.repository(SqlAccountRepository)


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


class SqlBoardOnboardingUnitOfWork(SqlUnitOfWork, BoardOnboardingUnitOfWork):
    """Транзакция над платами системы.

    Attributes:
        session_factory: Фабрика, дающая сессию блока.
    """

    @property
    def boards(self) -> BoardRepository:
        """Хранилище сопряжённых плат нынешней транзакции."""
        return self.repository(SqlBoardRepository)

    @property
    def claims(self) -> ClaimRepository:
        """Хранилище объявленных плат нынешней транзакции."""
        return self.repository(SqlClaimRepository)

    @property
    def networks(self) -> BoardNetworkRepository:
        """Хранилище сетей плат нынешней транзакции."""
        return self.repository(SqlBoardNetworkRepository)


def make_account_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> AccountUnitOfWorkFactory:
    """Строит фабрику границ транзакции над аккаунтами.

    Args:
        session_factory: Фабрика сессий.

    Returns:
        AccountUnitOfWorkFactory: Вызываемый объект, дающий свежую границу.
    """

    def factory() -> SqlAccountUnitOfWork:
        """Создаёт новую границу над аккаунтами."""
        return SqlAccountUnitOfWork(session_factory)

    return factory


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


def make_board_onboarding_unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> BoardOnboardingUnitOfWorkFactory:
    """Строит фабрику границ транзакции над платами.

    Args:
        session_factory: Фабрика сессий.

    Returns:
        BoardOnboardingUnitOfWorkFactory: Вызываемый объект, дающий свежую границу.
    """

    def factory() -> SqlBoardOnboardingUnitOfWork:
        """Создаёт новую границу над платами."""
        return SqlBoardOnboardingUnitOfWork(session_factory)

    return factory
