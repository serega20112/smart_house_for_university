"""Граница транзакции присвоения плат.

Взятие платы записывает и предложение, и строку платы, и они должны появиться
вместе, иначе никто ничего не получит. Поэтому эта граница отдельна от дома: она
короткая, про владение железом и не должна утянуть за собой переписывание панели.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from backend.application.interfaces.repositories.board_repository import (
    BoardNetworkRepository,
    BoardRepository,
    ClaimRepository,
)
from backend.application.interfaces.repositories.device_repository import DeviceRepository
from backend.application.interfaces.unit_of_work.transaction import TransactionalUnitOfWork


class BoardOnboardingUnitOfWork(TransactionalUnitOfWork):
    """Транзакция над платами системы."""

    @property
    @abstractmethod
    def boards(self) -> BoardRepository:
        """Репозиторий сопряжённых плат текущей транзакции."""

    @property
    @abstractmethod
    def devices(self) -> DeviceRepository:
        """Репозиторий устройств текущей транзакции.

        Устройства нужны именно здесь, потому что судьба платы и судьба её
        каналов решается одной транзакцией.
        """

    @property
    @abstractmethod
    def claims(self) -> ClaimRepository:
        """Репозиторий объявленных плат текущей транзакции."""

    @property
    @abstractmethod
    def networks(self) -> BoardNetworkRepository:
        """Репозиторий сетей плат текущей транзакции."""


class BoardOnboardingUnitOfWorkFactory(Protocol):
    """Создаёт свежую границу транзакции плат."""

    def __call__(self) -> BoardOnboardingUnitOfWork:
        """Возвращает новую границу."""
