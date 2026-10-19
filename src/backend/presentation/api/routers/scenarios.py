"""Scenario routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.application.dto.scenario import CreateScenarioCommand
from backend.domain.enums.device import parse_capability
from backend.domain.enums.operation import OperationStatus
from backend.domain.enums.scenario import CompletionBehavior
from backend.presentation.api.errors import raise_for_status
from backend.presentation.api.messages import (
    not_found_message,
    scenario_cancelled_message,
)
from backend.presentation.api.requests import ScenarioCreateBody
from backend.presentation.api.responses import OperationResponse, ScenarioResponse
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
async def list_scenarios(
    container: AppContainer, user_id: CurrentUserId
) -> list[ScenarioResponse]:
    """Return the scenarios currently occupying the control priority.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        list[ScenarioResponse]: Active scenarios.
    """
    scenarios = await container.get_active_scenarios.execute(user_id)
    return [ScenarioResponse.from_scenario(scenario) for scenario in scenarios]


@router.post("")
async def create_scenario(
    body: ScenarioCreateBody, container: AppContainer, user_id: CurrentUserId
) -> ScenarioResponse:
    """Schedule a new timed scenario.

    Args:
        body: Scenario description.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        ScenarioResponse: The created scenario.
    """
    scenario = await container.create_scenario.execute(
        user_id,
        CreateScenarioCommand(
            delay_minutes=body.delay_minutes,
            target_temperature=body.target_temperature,
            capability=parse_capability(body.capability),
            completion_behavior=_completion_behavior(body.completion_behavior),
            target=body.target,
        )
    )
    return ScenarioResponse.from_scenario(scenario)


@router.delete("/{scenario_id}")
async def cancel_scenario(
    scenario_id: int, container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Cancel a scenario.

    Args:
        scenario_id: Identifier of the scenario.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: Result of the cancellation.

    Raises:
        HTTPException: When the scenario does not exist.
    """
    status, _scenario = await container.cancel_scenario.execute(user_id, scenario_id)
    message = scenario_cancelled_message(scenario_id)
    if status is OperationStatus.NOT_FOUND:
        raise_for_status(status, not_found_message("Сценарий", scenario_id))
    raise_for_status(status, message)
    return OperationResponse(status=status.value, message=message)


def _completion_behavior(raw: str) -> CompletionBehavior:
    try:
        return CompletionBehavior(raw)
    except ValueError:
        return CompletionBehavior.CONTINUE_AUTOMATION
