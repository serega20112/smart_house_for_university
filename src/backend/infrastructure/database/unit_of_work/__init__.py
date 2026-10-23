"""Границы транзакций: одна сессия, одна транзакция, свои хранилища."""

from __future__ import annotations

from backend.infrastructure.database.unit_of_work.accounts import (
    SqlAccountUnitOfWork,
    make_account_unit_of_work,
)
from backend.infrastructure.database.unit_of_work.base import SessionBound, SqlUnitOfWork
from backend.infrastructure.database.unit_of_work.boards import (
    SqlBoardOnboardingUnitOfWork,
    make_board_onboarding_unit_of_work,
)
from backend.infrastructure.database.unit_of_work.home import (
    SqlHomeUnitOfWork,
    make_home_unit_of_work,
)

__all__ = [
    "SessionBound",
    "SqlAccountUnitOfWork",
    "SqlBoardOnboardingUnitOfWork",
    "SqlHomeUnitOfWork",
    "SqlUnitOfWork",
    "make_account_unit_of_work",
    "make_board_onboarding_unit_of_work",
    "make_home_unit_of_work",
]
