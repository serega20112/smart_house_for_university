"""Scenario repository port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from backend.domain.identifiers import ScenarioId, UserId
from backend.domain.scenarios.scenario import Scenario


class ScenarioRepository(Protocol):
    """Storage of the timed scenarios of one account."""

    async def list_all(self, user_id: UserId) -> Sequence[Scenario]:
        """Return every scenario of an account, newest first.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            Sequence[Scenario]: Stored scenarios.
        """

    async def list_holding_priority(self, user_id: UserId) -> Sequence[Scenario]:
        """Return the scenarios that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            Sequence[Scenario]: Pending and running scenarios.
        """

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> Scenario | None:
        """Return one scenario of an account.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            Scenario | None: Scenario, or None when the account has no such one.
        """

    async def add(self, scenario: Scenario) -> None:
        """Store a newly scheduled scenario.

        Args:
            scenario: Scenario to persist.

        Returns:
            None.
        """

    async def update(self, scenario: Scenario) -> None:
        """Store a changed scenario.

        Args:
            scenario: Scenario to persist.

        Returns:
            None.
        """
