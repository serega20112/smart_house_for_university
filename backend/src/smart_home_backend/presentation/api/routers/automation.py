"""Automation routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from smart_home_backend.presentation.api.requests import AutomationUpdateBody
from smart_home_backend.presentation.api.responses import (
    AutomationResponse,
    OperationResponse,
    SettingsResponse,
    automation_toggled_response,
    settings_saved_response,
)
from smart_home_backend.presentation.dependencies import get_container

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("")
async def get_automation(request: Request) -> AutomationResponse:
    """Return the current automation settings.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        AutomationResponse: Stored settings.
    """
    container = get_container(request)
    settings = await container.get_automation_settings.execute()
    return AutomationResponse.from_settings(settings)


@router.put("")
async def update_automation(body: AutomationUpdateBody, request: Request) -> SettingsResponse:
    """Apply a partial update to the automation settings.

    Args:
        body: Fields to change.
        request: Incoming request carrying the dependency container.

    Returns:
        SettingsResponse: Result of the update.
    """
    container = get_container(request)
    _status, settings = await container.update_automation.execute(body.to_command())
    return settings_saved_response(settings)


@router.post("/enable")
async def enable_automation(request: Request) -> SettingsResponse:
    """Turn the automation mode on.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        SettingsResponse: Result of the change.
    """
    container = get_container(request)
    _status, settings = await container.toggle_automation.execute(True)
    return automation_toggled_response(settings, True)


@router.post("/disable")
async def disable_automation(request: Request) -> SettingsResponse:
    """Turn the automation mode off.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        SettingsResponse: Result of the change.
    """
    container = get_container(request)
    _status, settings = await container.toggle_automation.execute(False)
    return automation_toggled_response(settings, False)


@router.post("/run")
async def run_automation_cycle(request: Request) -> OperationResponse:
    """Run a single automation cycle on demand.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        OperationResponse: What the cycle did.
    """
    container = get_container(request)
    cycle = await container.run_automation_cycle.execute()
    return OperationResponse(
        status=cycle.status.value,
        message=cycle.skipped_reason or "ok",
        data={"demands": cycle.demands, "actions": [action.status.value for action in cycle.actions]},
    )
