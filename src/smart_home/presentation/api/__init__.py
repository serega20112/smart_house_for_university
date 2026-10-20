"""REST API assembly.

The auth router is the only public part: it is what establishes the session
every other route depends on.
"""

from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.presentation.api.routers import (
    auth,
    automation,
    commands,
    devices,
    esp_devices,
    esp_networks,
    scenarios,
    state,
    system,
    voice,
)

api_router = APIRouter(route_class=DishkaRoute)
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(state.router)
api_router.include_router(devices.router)
api_router.include_router(esp_devices.router)
api_router.include_router(esp_networks.router)
api_router.include_router(automation.router)
api_router.include_router(scenarios.router)
api_router.include_router(commands.router)
api_router.include_router(voice.router)
