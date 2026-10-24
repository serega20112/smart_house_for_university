from __future__ import annotations

import httpx
import pytest

from backend import __version__
from backend.composition.app import build_api_app
from backend.config.settings import Settings


@pytest.mark.asyncio
async def test_app_health_returns_the_package_version() -> None:
    application = build_api_app(Settings())

    transport = httpx.ASGITransport(app=application)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    async with client, application.router.lifespan_context(application):
        response = await client.get("/api/health")

    assert response.status_code == 200
    document = response.json()
    assert document["status"] == "ok"
    assert document["version"] == __version__


@pytest.mark.asyncio
async def test_app_ready_reports_each_dependency() -> None:
    application = build_api_app(Settings())

    transport = httpx.ASGITransport(app=application)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    async with client:
        response = await client.get("/api/ready")

    assert response.status_code in (200, 503)
    document = response.json()
    assert set(document["dependencies"]) == {"database", "redis"}
    assert document["status"] in ("ready", "unavailable")
