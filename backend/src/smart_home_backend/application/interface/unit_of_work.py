"""Unit of work abstraction for the application layer.

Use cases resolve repositories inside an ``async with`` boundary and persist the
work on exit. The concrete transaction owner lives in the infrastructure layer,
which keeps SQLAlchemy sessions out of the application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Protocol

from smart_home_backend.application.interface.repositories.automation_repository import (
    AutomationRepository,
)
from smart_home_backend.application.interface.repositories.device_repository import (
    DeviceRepository,
)
from smart_home_backend.application.interface.repositories.scenario_repository import (
    ScenarioRepository,
)


class UnitOfWork(ABC):
    """Transaction boundary exposing the repositories of one unit of work."""

    @property
    @abstractmethod
    def devices(self) -> DeviceRepository:
        """Return the device repository bound to the current transaction.

        Returns:
            DeviceRepository: Device repository.
        """

    @property
    @abstractmethod
    def automation(self) -> AutomationRepository:
        """Return the automation repository bound to the current transaction.

        Returns:
            AutomationRepository: Automation repository.
        """

    @property
    @abstractmethod
    def scenarios(self) -> ScenarioRepository:
        """Return the scenario repository bound to the current transaction.

        Returns:
            ScenarioRepository: Scenario repository.
        """

    @abstractmethod
    async def commit(self) -> None:
        """Persist all pending changes atomically.

        Returns:
            None.
        """

    @abstractmethod
    async def rollback(self) -> None:
        """Discard all pending changes.

        Returns:
            None.
        """

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the unit of work boundary.

        Returns:
            UnitOfWork: Self for use inside the with block.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Commit on success and roll back on failure.

        Args:
            exc_type: Raised exception type or None.
            exc_val: Raised exception value or None.
            exc_tb: Raised exception traceback or None.

        Returns:
            bool: False so exceptions propagate.
        """
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
        return False


class UnitOfWorkFactory(Protocol):
    """Callable producing a fresh unit of work.

    Args:
        None.

    Returns:
        UnitOfWork: New unit of work.
    """

    def __call__(self) -> UnitOfWork:
        """Create a new unit of work.

        Returns:
            UnitOfWork: New unit of work.
        """
