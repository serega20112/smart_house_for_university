"""Read side of the timed scenarios."""

from __future__ import annotations

from typing import Protocol

from smart_home.application.dto.scenario import ScenarioView
from smart_home.domain.identifiers import ScenarioId, UserId


class ScenarioQueries(Protocol):
    """Reads of the timed scenarios."""

    async def list_all(self, user_id: UserId) -> list[ScenarioView]:
        """Return every scenario of an account.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Scenarios shaped for display.
        """

    async def list_holding_priority(self, user_id: UserId) -> list[ScenarioView]:
        """Return the scenarios that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Pending and running scenarios.
        """

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView | None:
        """Return one scenario of an account.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            ScenarioView | None: Scenario, or None when the account has no such one.
        """

    async def latest_holding_priority(self, user_id: UserId) -> ScenarioView | None:
        """Return the most recently scheduled scenario still holding priority.

        "The scenario I meant" is the one that was asked for last, so choosing it
        is a property of the stored data rather than a guess about list order.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            ScenarioView | None: Matching scenario, or None when there is none.
        """
