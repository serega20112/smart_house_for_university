"""System routes.

The health probe stays public because an orchestrator has no session, while
everything describing a home is resolved from the bearer token like every other
protected endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.presentation.api.mappers import reading_payload
from backend.presentation.api.responses import (
    AutomationResponse,
    DeviceResponse,
    HomeStateResponse,
    ScenarioResponse,
)
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the availability of the backend.

    Args:
        None.

    Returns:
        dict[str, str]: Availability report.
    """
    return {"backend": "online"}


@router.get("/state")
async def home_state(
    container: AppContainer, user_id: CurrentUserId
) -> HomeStateResponse:
    """Return the full snapshot shown on the main screen.

    The snapshot is assembled from the stored configuration and the live state
    of one account only, which is what makes the single frontend show a
    different home to every signed in user.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        HomeStateResponse: Snapshot of the home of the current user.
    """
    snapshot = await container.get_home_snapshot.execute(user_id)
    devices = await container.get_devices.execute(user_id)
    runtime = container.runtimes.for_user(user_id)
    return HomeStateResponse(
        backend_online=True,
        esp_online=snapshot.esp_online,
        manual_override=snapshot.manual_override,
        **reading_payload(snapshot.reading),
        devices=[
            DeviceResponse.from_device(device, runtime.device_status(device).value)
            for device in devices
        ],
        automation=AutomationResponse.from_settings(snapshot.automation),
        active_scenarios=[
            ScenarioResponse.from_scenario(scenario) for scenario in snapshot.active_scenarios
        ],
    )
