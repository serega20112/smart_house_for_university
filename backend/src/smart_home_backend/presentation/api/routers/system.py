"""System routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from smart_home_backend.infrastructure.di import Container
from smart_home_backend.presentation.api.mappers import reading_payload
from smart_home_backend.presentation.api.responses import (
    AutomationResponse,
    DeviceResponse,
    HomeStateResponse,
    ScenarioResponse,
)
from smart_home_backend.presentation.dependencies import get_container

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Return the availability of the backend and the board.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        dict[str, str]: Availability report.
    """
    container = get_container(request)
    return {
        "backend": "online",
        "esp": "online" if container.runtime.esp_online else "offline",
    }


@router.get("/state")
async def home_state(request: Request) -> HomeStateResponse:
    """Return the full snapshot shown on the main screen.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        HomeStateResponse: Snapshot of the home state.
    """
    container = get_container(request)
    snapshot = await container.get_home_snapshot.execute()
    devices = await container.get_devices.execute()
    return HomeStateResponse(
        backend_online=True,
        esp_online=snapshot.esp_online,
        manual_override=snapshot.manual_override,
        **reading_payload(snapshot.reading),
        devices=[_device_response(container, device) for device in devices],
        automation=AutomationResponse.from_settings(snapshot.automation),
        active_scenarios=[
            ScenarioResponse.from_scenario(scenario) for scenario in snapshot.active_scenarios
        ],
    )


def _device_response(container: Container, device) -> DeviceResponse:
    return DeviceResponse.from_device(device, container.runtime.device_status(device).value)
