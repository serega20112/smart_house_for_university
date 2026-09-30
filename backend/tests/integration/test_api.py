"""Tests of the REST API surface."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from smart_home_backend.config import Settings
from smart_home_backend.infrastructure.database import create_schema
from smart_home_backend.infrastructure.di import build_container
from smart_home_backend.presentation.app_factory import create_app


@pytest.fixture
async def client(settings: Settings, events, board) -> AsyncClient:
    container = build_container(settings, events)
    await create_schema(container.engine)
    container.runtime.set_esp_online(True)
    app = create_app(settings)
    app.state.container = container
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance
    await container.engine.dispose()


async def create_device(client: AsyncClient, name: str, channel: int = 1) -> int:
    response = await client.post(
        "/api/devices",
        json={"name": name, "type": "LIGHT", "physical_channel": channel},
    )
    return response.json()["data"]["id"]


async def test_health_reports_the_board(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"backend": "online", "esp": "online"}


async def test_state_returns_the_full_snapshot(client: AsyncClient) -> None:
    payload = (await client.get("/api/state")).json()
    assert payload["esp_online"] is True
    assert payload["manual_override"] is False
    assert payload["automation"]["target_temperature"] == 22.0
    assert payload["devices"] == []
    assert payload["active_scenarios"] == []


async def test_device_is_created_and_listed(client: AsyncClient) -> None:
    created = await client.post(
        "/api/devices", json={"name": "Лампа", "type": "LIGHT", "physical_channel": 1}
    )
    assert created.status_code == 200
    assert created.json()["status"] == "SUCCESS"

    listed = await client.get("/api/devices")
    assert [device["name"] for device in listed.json()] == ["Лампа"]


async def test_conflicting_channel_is_rejected(client: AsyncClient) -> None:
    await create_device(client, "Лампа")
    conflict = await client.post(
        "/api/devices", json={"name": "Дубль", "type": "LIGHT", "physical_channel": 1}
    )
    assert conflict.status_code == 409


async def test_device_is_updated(client: AsyncClient) -> None:
    device_id = await create_device(client, "Лампа")
    updated = await client.patch(f"/api/devices/{device_id}", json={"name": "Люстра"})
    assert updated.status_code == 200
    assert (await client.get(f"/api/devices/{device_id}")).json()["name"] == "Люстра"


async def test_missing_device_returns_not_found(client: AsyncClient) -> None:
    assert (await client.get("/api/devices/999")).status_code == 404


async def test_device_is_deleted(client: AsyncClient) -> None:
    device_id = await create_device(client, "Лампа")
    assert (await client.delete(f"/api/devices/{device_id}")).status_code == 200
    assert (await client.delete(f"/api/devices/{device_id}")).status_code == 404


async def test_unknown_mode_is_rejected(client: AsyncClient) -> None:
    device_id = await create_device(client, "Лампа")
    response = await client.post(f"/api/devices/{device_id}/mode", json={"mode": "DANCE"})
    assert response.status_code == 422


async def test_device_is_switched_on_through_the_api(
    client: AsyncClient, board
) -> None:
    device_id = await create_device(client, "Лампа")
    response = await client.post(f"/api/devices/{device_id}/on")
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert board.commands == [(1, True)]


async def test_offline_board_returns_service_unavailable(
    client: AsyncClient, board
) -> None:
    device_id = await create_device(client, "Лампа")
    board.go_offline()
    response = await client.post(f"/api/devices/{device_id}/on")
    assert response.status_code == 503


async def test_automation_settings_are_read_and_updated(client: AsyncClient) -> None:
    assert (await client.get("/api/automation")).json()["enabled"] is False

    updated = await client.put("/api/automation", json={"enabled": True})
    assert updated.json()["automation"]["enabled"] is True

    disabled = await client.post("/api/automation/disable")
    assert disabled.json()["automation"]["enabled"] is False


async def test_automation_cycle_endpoint_reports_the_skip_reason(client: AsyncClient) -> None:
    assert (await client.post("/api/automation/run")).json()["message"] == "automation_disabled"


async def test_scenario_is_created_and_cancelled(client: AsyncClient) -> None:
    created = await client.post(
        "/api/scenarios",
        json={"delay_minutes": 30, "target_temperature": 20.0, "capability": "COOL"},
    )
    scenario_id = created.json()["id"]
    assert (await client.get("/api/scenarios")).json()[0]["id"] == scenario_id

    assert (await client.delete(f"/api/scenarios/{scenario_id}")).status_code == 200
    assert (await client.delete(f"/api/scenarios/{scenario_id}")).status_code == 404


async def test_free_form_command_is_answered(client: AsyncClient, board) -> None:
    await create_device(client, "Лампа")
    response = await client.post("/api/commands", json={"text": "включи свет"})
    assert response.status_code == 200
    assert response.json()["intent"] == "TURN_ON"
    assert board.commands == [(1, True)]


async def test_command_answer_is_rendered_for_the_user(client: AsyncClient) -> None:
    response = await client.post("/api/commands", json={"text": "какая температура"})
    assert response.json()["message"]


async def test_device_switch_publishes_a_realtime_event(
    client: AsyncClient, board, events
) -> None:
    device_id = await create_device(client, "Лампа")
    await client.post(f"/api/devices/{device_id}/on")
    assert "device.state_changed" in events.types()
