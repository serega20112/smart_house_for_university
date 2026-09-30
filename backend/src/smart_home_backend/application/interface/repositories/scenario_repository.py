"""Scenario repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from smart_home_backend.domain.entities.scenario import Scenario


class ScenarioRepository(ABC):
    """Storage of timed scenarios."""

    @abstractmethod
    async def list_all(self) -> Sequence[Scenario]:
        """Return every scenario, newest first.

        Returns:
            Sequence[Scenario]: Stored scenarios.
        """

    @abstractmethod
    async def list_active(self) -> Sequence[Scenario]:
        """Return pending and running scenarios.

        Returns:
            Sequence[Scenario]: Active scenarios.
        """

    @abstractmethod
    async def get(self, scenario_id: int) -> Scenario | None:
        """Return a scenario by id.

        Args:
            scenario_id: Identifier of the scenario.

        Returns:
            Scenario | None: Scenario or None when it does not exist.
        """

    @abstractmethod
    async def save(self, scenario: Scenario) -> Scenario:
        """Create or update a scenario.

        Args:
            scenario: Scenario to persist.

        Returns:
            Scenario: Persisted scenario including its identifier.
        """

    @abstractmethod
    async def delete(self, scenario_id: int) -> bool:
        """Delete a scenario.

        Args:
            scenario_id: Identifier of the scenario.

        Returns:
            bool: True when a scenario was removed.
        """
