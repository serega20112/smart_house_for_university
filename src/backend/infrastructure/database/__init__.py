"""Слой хранения бэкенда.

Этот пакет — единственное место в системе, знающее, что база данных существует. Домен
решает, что такое агрегат, приложение — когда изменение должно случиться, а всё нижнее —
адаптеры: строки, запросы, сессии и по одной границе транзакции на жизнь.

Схему применяют ревизиями Alembic из ``build/alembic/versions`` и отсюда не создают
никогда, поэтому развёртывание всегда способно построить её с нуля, а схему можно
прочитать как разность в ревью.

Модули:

``tables``
    декларативное описание всякой таблицы и метаданные, с которыми сверяют ревизии.
``mappers``
    чистые функции, переводящие агрегаты в строки и строки обратно в агрегаты.
``repositories``
    сторона записи: по хранилищу на агрегат, все делят сессию границы транзакции.
``queries``
    сторона чтения: отвечает моделями чтения прикладного слоя и транзакцию не открывает.
``unit_of_work``
    границы транзакций, по одной на жизнь, и их фабрики.
``engine``
    асинхронный движок и фабрика сессий, которые композиционный корень строит один раз.
"""

from backend.infrastructure.database.engine import build_engine, build_session_factory
from backend.infrastructure.database.queries import (
    SqlAccountQueries,
    SqlAutomationQueries,
    SqlBoardQueries,
    SqlDeviceQueries,
    SqlScenarioQueries,
)
from backend.infrastructure.database.repositories import (
    SqlAccountRepository,
    SqlAutomationRepository,
    SqlBoardNetworkRepository,
    SqlBoardRepository,
    SqlClaimRepository,
    SqlDashboardRepository,
    SqlDeviceRepository,
    SqlPreferencesRepository,
    SqlScenarioRepository,
)
from backend.infrastructure.database.tables import Base
from backend.infrastructure.database.unit_of_work import (
    SqlAccountUnitOfWork,
    SqlBoardOnboardingUnitOfWork,
    SqlHomeUnitOfWork,
    SqlUnitOfWork,
    make_account_unit_of_work,
    make_board_onboarding_unit_of_work,
    make_home_unit_of_work,
)

__all__ = [
    "Base",
    "SqlAccountQueries",
    "SqlAccountRepository",
    "SqlAccountUnitOfWork",
    "SqlAutomationQueries",
    "SqlAutomationRepository",
    "SqlBoardNetworkRepository",
    "SqlBoardOnboardingUnitOfWork",
    "SqlBoardQueries",
    "SqlBoardRepository",
    "SqlClaimRepository",
    "SqlDashboardRepository",
    "SqlDeviceQueries",
    "SqlDeviceRepository",
    "SqlHomeUnitOfWork",
    "SqlPreferencesRepository",
    "SqlScenarioQueries",
    "SqlScenarioRepository",
    "SqlUnitOfWork",
    "build_engine",
    "build_session_factory",
    "make_account_unit_of_work",
    "make_board_onboarding_unit_of_work",
    "make_home_unit_of_work",
]
