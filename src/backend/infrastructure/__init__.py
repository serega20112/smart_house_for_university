"""Infrastructure layer.

Adapters for everything the application talks to: the database, the board, the
notification channels and the natural language pipeline.

Only the database adapter is re-exported here. The rest of the adapters are
imported from their own modules, so importing the layer never drags in a
subsystem a process does not use.
"""

from backend.infrastructure.database import (
    Base,
    SqlAccountUnitOfWork,
    SqlBoardOnboardingUnitOfWork,
    SqlHomeUnitOfWork,
    build_engine,
    build_session_factory,
    make_account_unit_of_work,
    make_board_onboarding_unit_of_work,
    make_home_unit_of_work,
)

__all__ = [
    "Base",
    "SqlAccountUnitOfWork",
    "SqlBoardOnboardingUnitOfWork",
    "SqlHomeUnitOfWork",
    "build_engine",
    "build_session_factory",
    "make_account_unit_of_work",
    "make_board_onboarding_unit_of_work",
    "make_home_unit_of_work",
]
