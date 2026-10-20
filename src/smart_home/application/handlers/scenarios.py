"""Handlers of the intents that deal with timed scenarios."""

from __future__ import annotations

from smart_home.application.dto.home import CommandReply
from smart_home.application.errors import CommandNotUnderstoodError, ScenarioNotFoundError
from smart_home.application.ports.language import ClarificationReason, CommandUnderstanding, Intent
from smart_home.application.ports.queries.scenarios import ScenarioQueries
from smart_home.application.services.scenario_service import ScenarioService
from smart_home.domain.climate.climate_demand import DemandCalculator
from smart_home.domain.identifiers import ScenarioId, UserId
from smart_home.domain.scenarios.completion_behavior import CompletionBehavior
from smart_home.domain.scenarios.scenario_action import ScenarioAction


class ScheduleScenarioHandler:
    """Answers "make it twenty degrees in half an hour"."""

    def __init__(self, scenarios: ScenarioService, demands: DemandCalculator) -> None:
        """Initialize the handler.

        Args:
            scenarios: Service owning the lifecycle of the scenarios.
            demands: Model component deciding which capability a target implies.

        Returns:
            None.
        """
        self._scenarios = scenarios
        self._demands = demands

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Schedule the scenario the sentence asks for.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: The scenario that was scheduled.

        Raises:
            CommandNotUnderstoodError: When neither a capability nor a target can
            be worked out.
        """
        capability = parsed.capability
        if capability is None and parsed.temperature is not None:
            capability = self._demands.capability_towards(parsed.temperature.celsius, None)
        if capability is None:
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_CAPABILITY)
        action = ScenarioAction(capability=capability, target_temperature=parsed.temperature)
        view = await self._scenarios.schedule(
            user_id=user_id,
            actions=(action,),
            delay_minutes=parsed.delay_minutes,
            target=parsed.target,
            completion_behavior=CompletionBehavior.LEAVE_TO_AUTOMATION,
            duration_minutes=parsed.delay_minutes,
        )
        return CommandReply(
            intent=Intent.SCHEDULE_SCENARIO,
            answer="",
            details={"scenario_id": str(view.id), "start_at": view.start_at.isoformat()},
        )


class CancelScenarioHandler:
    """Answers "cancel the scenario"."""

    def __init__(self, scenarios: ScenarioService, scenario_queries: ScenarioQueries) -> None:
        """Initialize the handler.

        Args:
            scenarios: Service owning the lifecycle of the scenarios.
            scenario_queries: Reads used to work out which scenario was meant.

        Returns:
            None.
        """
        self._scenarios = scenarios
        self._queries = scenario_queries

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Cancel the scenario the sentence points at.

        "The scenario I meant" is the one that was asked for last, and that choice
        is made by the read side rather than by picking whatever came first in a
        list.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: The scenario that was cancelled.

        Raises:
            ScenarioNotFoundError: When the account has no scenario to cancel.
        """
        del parsed
        target = await self._queries.latest_holding_priority(user_id)
        if target is None:
            raise ScenarioNotFoundError(ScenarioId.generate())
        view = await self._scenarios.cancel(user_id, ScenarioId.parse(target.id))
        return CommandReply(
            intent=Intent.CANCEL_SCENARIO,
            answer="",
            details={"scenario_id": str(view.id), "status": view.status.value},
        )
