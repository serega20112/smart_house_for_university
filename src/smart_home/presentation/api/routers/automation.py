"""Automation routes.

Automation is the part of the system that acts on its own, so the interface
shows the current configuration and changes it. Whether a target is reachable is
a question of the domain, and the domain answers it by refusing the change.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.application.dto import (
    AutomationPatch,
    DeviceId,
    Humidity,
    Temperature,
)
from smart_home.application.ports.queries.automation import AutomationQueries
from smart_home.application.use_cases.automation.update_automation import (
    UpdateAutomationUseCase,
)
from smart_home.presentation.api.schemas import (
    AutomationResponse,
    AutomationUpdateBody,
    automation_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/automation", tags=["automation"])


@router.get("", response_model=AutomationResponse)
async def read_automation(
    user_id: CurrentUserId, queries: FromDishka[AutomationQueries]
) -> AutomationResponse:
    """Return the automation configuration of the current account.

    Args:
        user_id: Owner resolved from the bearer token.
        queries: Reads of the automation configuration.

    Returns:
        AutomationResponse: Configuration of the account.
    """
    return automation_of(await queries.get(user_id))


@router.put("", response_model=AutomationResponse)
async def update_automation(
    body: AutomationUpdateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[UpdateAutomationUseCase],
) -> AutomationResponse:
    """Apply a partial change to the automation configuration.

    Args:
        body: Fields to change.
        user_id: Owner resolved from the bearer token.
        use_case: Change of the configuration.

    Returns:
        AutomationResponse: Configuration as it is now.
    """
    automation = await use_case.execute(user_id, _patch_of(body))
    return automation_of(automation)


def _patch_of(body: AutomationUpdateBody) -> AutomationPatch:
    """Return the command of a partial change.

    Args:
        body: Fields to change.

    Returns:
        AutomationPatch: Command understood by the use case.
    """
    return AutomationPatch(
        enabled=body.enabled,
        target_temperature=(
            None if body.target_temperature is None else Temperature(body.target_temperature)
        ),
        temperature_tolerance=body.temperature_tolerance,
        target_humidity=(None if body.target_humidity is None else Humidity(body.target_humidity)),
        humidity_tolerance=body.humidity_tolerance,
        participating_device_ids=(
            None
            if body.participating_device_ids is None
            else frozenset(DeviceId.parse(item) for item in body.participating_device_ids)
        ),
    )
