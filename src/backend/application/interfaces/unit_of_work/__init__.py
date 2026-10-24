"""Границы транзакций прикладного слоя.

Граница принадлежит приложению, а транзакцию владеет реализация: use case знает
только этот контракт, поэтому работа с сессией БД не расползается по слою.
"""

from backend.application.interfaces.unit_of_work.account import (
    AccountUnitOfWork,
    AccountUnitOfWorkFactory,
)
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWork,
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.interfaces.unit_of_work.home import (
    HomeUnitOfWork,
    HomeUnitOfWorkFactory,
)
from backend.application.interfaces.unit_of_work.transaction import TransactionalUnitOfWork

__all__ = [
    "AccountUnitOfWork",
    "AccountUnitOfWorkFactory",
    "BoardOnboardingUnitOfWork",
    "BoardOnboardingUnitOfWorkFactory",
    "HomeUnitOfWork",
    "HomeUnitOfWorkFactory",
    "TransactionalUnitOfWork",
]
