"""Scenario routes.

A scenario is a promise the user made to their own house, so the interface only
schedules one, lists them and cancels them. Everything that happens afterwards
belongs to the background cycles of the system.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.application.dto import (
    ScenarioAction,
    ScenarioId,
    ScheduleScenarioCommand,
    Temperature,
)
from smart_home.application.ports.queries.scenarios import ScenarioQueries
from smart_home.application.services.scenario_service import ScenarioService
from smart_home.presentation.api.schemas import (
    ScenarioCreateBody,
    ScenarioResponse,
    scenario_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(
    user_id: CurrentUserId, queries: FromDishka[ScenarioQueries]
) -> list[ScenarioResponse]:
    """Return every scenario of the current account.

    Args:
        user_id: Owner resolved from the bearer token.
        queries: Reads of the scenarios.

    Returns:
        list[ScenarioResponse]: Scenarios of the account.
    """
    scenarios = await queries.list_all(user_id)
    return [scenario_of(scenario) for scenario in scenarios]


@router.post("", response_model=ScenarioResponse)
async def schedule_scenario(
    body: ScenarioCreateBody,
    user_id: CurrentUserId,
    service: FromDishka[ScenarioService],
) -> ScenarioResponse:
    """Schedule a scenario waiting for its start moment.

    Args:
        body: The deferred action the user asked for.
        user_id: Owner resolved from the bearer token.
        service: Lifecycle of the scenarios.

    Returns:
        ScenarioResponse: The stored scenario.
    """
    action = ScenarioAction(
        capability=body.capability,
        target_temperature=(
            None if body.target_temperature is None else Temperature(body.target_temperature)
        ),
    )
    scenario = await service.schedule(
        user_id,
        ScheduleScenarioCommand(
            action=action,
            delay_minutes=body.delay_minutes,
            target=body.target,
            completion_behavior=body.completion_behavior,
            duration_minutes=body.duration_minutes,
        ),
    )
    return scenario_of(scenario)


@router.delete("/{scenario_id}", response_model=ScenarioResponse)
async def cancel_scenario(
    scenario_id: str,
    user_id: CurrentUserId,
    service: FromDishka[ScenarioService],
) -> ScenarioResponse:
    """Give a scenario up.

    Args:
        scenario_id: Identifier of the scenario.
        user_id: Owner resolved from the bearer token.
        service: Lifecycle of the scenarios.

    Returns:
        ScenarioResponse: The cancelled scenario.
    """
    scenario = await service.cancel(user_id, ScenarioId.parse(scenario_id))
    return scenario_of(scenario)
