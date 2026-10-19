"""Automation routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.presentation.api.requests import AutomationUpdateBody
from backend.presentation.api.responses import (
    AutomationResponse,
    OperationResponse,
    SettingsResponse,
    automation_toggled_response,
    settings_saved_response,
)
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("")
async def get_automation(
    container: AppContainer, user_id: CurrentUserId
) -> AutomationResponse:
    """Return the current automation settings.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        AutomationResponse: Stored settings.
    """
    settings = await container.get_automation_settings.execute(user_id)
    return AutomationResponse.from_settings(settings)


@router.put("")
async def update_automation(
    body: AutomationUpdateBody, container: AppContainer, user_id: CurrentUserId
) -> SettingsResponse:
    """Apply a partial update to the automation settings.

    Args:
        body: Fields to change.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        SettingsResponse: Result of the update.
    """
    _status, settings = await container.update_automation.execute(user_id, body.to_command())
    return settings_saved_response(settings)


@router.post("/enable")
async def enable_automation(
    container: AppContainer, user_id: CurrentUserId
) -> SettingsResponse:
    """Turn the automation mode on.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        SettingsResponse: Result of the change.
    """
    _status, settings = await container.toggle_automation.execute(user_id, True)
    return automation_toggled_response(settings, True)


@router.post("/disable")
async def disable_automation(
    container: AppContainer, user_id: CurrentUserId
) -> SettingsResponse:
    """Turn the automation mode off.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        SettingsResponse: Result of the change.
    """
    _status, settings = await container.toggle_automation.execute(user_id, False)
    return automation_toggled_response(settings, False)


@router.post("/run")
async def run_automation_cycle(
    container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Run a single automation cycle on demand.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: What the cycle did.
    """
    cycle = await container.run_automation_cycle.execute(user_id)
    return OperationResponse(
        status=cycle.status.value,
        message=cycle.skipped_reason or "ok",

        data={
            "demands": cycle.demands,
            "actions": [action.status.value for action in cycle.actions],
        },
    )
