"""System routes.

The health probe stays public because an orchestrator has no session, while
everything describing a home is resolved from the bearer token like every other
protected endpoint.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.application.dto import ApplicationVersion
from smart_home.config import Settings
from smart_home.presentation.api.schemas import HealthResponse

router = APIRouter(route_class=DishkaRoute, tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: FromDishka[Settings], version: FromDishka[ApplicationVersion]
) -> HealthResponse:
    """Return the availability of the service.

    Args:
        settings: Configuration the process runs with.
        version: Version of the running build.

    Returns:
        HealthResponse: Availability report.
    """
    return HealthResponse(
        status="ok",
        name=settings.app_name,
        version=version.value,
    )
