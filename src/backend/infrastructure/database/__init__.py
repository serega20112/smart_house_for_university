"""Persistence layer of the backend.

This package is the only place in the system that knows a database exists. The
domain decides what an aggregate is, the application decides when a change has to
happen, and everything below is an adapter: rows, statements, sessions and one
unit of work per lifecycle.

The schema is applied through the Alembic revisions in ``build/alembic/versions``
and never created from here, so a deployment can always rebuild it from zero and a
review can read the schema as a diff.

The modules are:

``tables``
    the declarative definition of every table, and the metadata the revisions are
    compared against.
``mappers``
    pure functions translating aggregates into rows and rows back into aggregates.
``repositories``
    the write side, one repository per aggregate, all sharing the session of the
    unit of work.
``queries``
    the read side, answering with the read models of the application layer and
    never opening a transaction.
``unit_of_work``
    the transaction boundaries, one per lifecycle, and their factories.
``engine``
    the async engine and the session factory the composition root builds once.
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
