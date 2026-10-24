"""Слой инфраструктуры.

Адаптеры ко всему, с чем говорит приложение: база данных, плата, каналы уведомлений и
конвейер понимания речи.

Отсюда переэкспортирован только адаптер базы. Остальные адаптеры читают из их собственных
модулей, поэтому импорт слоя ни за чем лишним процесс не тянет.
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
