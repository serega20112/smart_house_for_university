"""REST API assembly."""

from fastapi import APIRouter

from smart_home_backend.presentation.api.routers import (
    automation,
    commands,
    devices,
    scenarios,
    system,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(devices.router)
api_router.include_router(automation.router)
api_router.include_router(scenarios.router)
api_router.include_router(commands.router)
