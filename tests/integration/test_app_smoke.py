from __future__ import annotations

from importlib.metadata import version

import httpx
import pytest

from smart_home.bootstrap.version import DISTRIBUTION_NAME
from smart_home.config.settings import Settings
from smart_home.presentation.app_factory import create_app


@pytest.mark.asyncio
async def test_app_health_returns_the_package_version() -> None:
    application = create_app(Settings())

    transport = httpx.ASGITransport(app=application)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    async with client, application.router.lifespan_context(application):
        response = await client.get("/api/health")

    assert response.status_code == 200
    document = response.json()
    assert document["status"] == "ok"
    assert document["version"] == version(DISTRIBUTION_NAME)
