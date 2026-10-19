"""Per-user state routes.

The state lives on the server, not in the frontend: these endpoints return what
has to be rendered and accept what has to be remembered. The very same generic
components are reused for every account, only the data behind them differs.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.domain.enums.operation import OperationStatus
from backend.presentation.api.errors import raise_for_status
from backend.presentation.api.messages import (
    dashboard_saved_message,
    preferences_saved_message,
)
from backend.presentation.api.requests import (
    DashboardUpdateBody,
    PreferencesUpdateBody,
)
from backend.presentation.api.responses import (
    DashboardResponse,
    OperationResponse,
    PreferencesResponse,
)
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(tags=["state"])


@router.get("/preferences")
async def read_preferences(user_id: CurrentUserId, container: AppContainer) -> PreferencesResponse:
    """Return the interface preferences of the current user.

    Args:
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        PreferencesResponse: Stored preferences.
    """
    return PreferencesResponse.from_preferences(await container.get_preferences.execute(user_id))


@router.patch("/preferences")
async def update_preferences(
    body: PreferencesUpdateBody, user_id: CurrentUserId, container: AppContainer
) -> OperationResponse:
    """Store a partial update of the interface preferences.

    Args:
        body: Fields to change.
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        OperationResponse: Result of the update.

    Raises:
        HTTPException: When a value is outside the allowed set.
    """
    result, preferences = await container.update_preferences.execute(user_id, body.to_command())
    raise_for_status(result, preferences_saved_message())
    return OperationResponse(
        status=result.value,
        message=preferences_saved_message(),
        data=PreferencesResponse.from_preferences(preferences).model_dump(),
    )


@router.get("/dashboard")
async def read_dashboard(user_id: CurrentUserId, container: AppContainer) -> DashboardResponse:
    """Return the dashboard layout of the current user.

    Args:
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        DashboardResponse: Stored widget list.
    """
    return DashboardResponse.from_dashboard(await container.get_dashboard.execute(user_id))


@router.patch("/dashboard")
async def update_dashboard(
    body: DashboardUpdateBody, user_id: CurrentUserId, container: AppContainer
) -> OperationResponse:
    """Store the dashboard layout of the current user.

    Args:
        body: Widgets in the desired order.
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        OperationResponse: Result of the update.

    Raises:
        HTTPException: When a widget references something the user has not got.
    """
    result, dashboard = await container.update_dashboard.execute(user_id, body.to_command())
    if result is OperationStatus.INVALID_INPUT:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Виджет ссылается на неизвестное устройство или тип",
        )
    raise_for_status(result, dashboard_saved_message())
    return OperationResponse(
        status=result.value,
        message=dashboard_saved_message(),
        data=DashboardResponse.from_dashboard(dashboard).model_dump(),
    )
