"""Scenario routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from smart_home_backend.application.dto.scenario import CreateScenarioCommand
from smart_home_backend.domain.enums.device import parse_capability
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.domain.enums.scenario import CompletionBehavior
from smart_home_backend.presentation.api.errors import raise_for_status
from smart_home_backend.presentation.api.messages import (
    created_message,
    not_found_message,
    scenario_cancelled_message,
)
from smart_home_backend.presentation.api.requests import ScenarioCreateBody
from smart_home_backend.presentation.api.responses import OperationResponse, ScenarioResponse
from smart_home_backend.presentation.dependencies import get_container

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
async def list_scenarios(request: Request) -> list[ScenarioResponse]:
    """Return the scenarios currently occupying the control priority.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        list[ScenarioResponse]: Active scenarios.
    """
    container = get_container(request)
    scenarios = await container.get_active_scenarios.execute()
    return [ScenarioResponse.from_scenario(scenario) for scenario in scenarios]


@router.post("")
async def create_scenario(body: ScenarioCreateBody, request: Request) -> ScenarioResponse:
    """Schedule a new timed scenario.

    Args:
        body: Scenario description.
        request: Incoming request carrying the dependency container.

    Returns:
        ScenarioResponse: The created scenario.
    """
    container = get_container(request)
    scenario = await container.create_scenario.execute(
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
async def cancel_scenario(scenario_id: int, request: Request) -> OperationResponse:
    """Cancel a scenario.

    Args:
        scenario_id: Identifier of the scenario.
        request: Incoming request carrying the dependency container.

    Returns:
        OperationResponse: Result of the cancellation.

    Raises:
        HTTPException: When the scenario does not exist.
    """
    container = get_container(request)
    status, _scenario = await container.cancel_scenario.execute(scenario_id)
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
