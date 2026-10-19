"""Tests of the REST API surface.

The point of these tests is not that the endpoints answer, but that a session
only ever reaches the data of its own account.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from smart_home_backend.config import Settings
from smart_home_backend.infrastructure.database import create_schema
from smart_home_backend.infrastructure.di import build_container
from smart_home_backend.presentation.app_factory import create_app


@pytest_asyncio.fixture
async def client(settings: Settings, events, board) -> AsyncIterator[AsyncClient]:
    container = build_container(settings, events)
    await create_schema(container.engine)
    app = create_app(settings)
    app.state.container = container
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        instance.container = container  # type: ignore[attr-defined]
        yield instance
    await container.engine.dispose()


async def register(client: AsyncClient, email: str, name: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "super-secret-1", "display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}


@pytest.fixture
async def alice(client: AsyncClient) -> dict:
    return await register(client, "alice@example.com", "Алиса")


@pytest.fixture
async def bob(client: AsyncClient) -> dict:
    return await register(client, "bob@example.com", "Борис")


async def test_health_is_public(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"backend": "online"}


async def test_registration_returns_a_usable_session(client: AsyncClient, alice: dict) -> None:
    profile = await client.get("/api/auth/me", headers=auth(alice))
    assert profile.status_code == 200
    assert profile.json()["email"] == "alice@example.com"
    assert profile.json()["id"] == alice["user"]["id"]


async def test_repeated_login_is_refused(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "super-secret-1", "display_name": "Дубль"},
    )
    assert response.status_code == 201
    again = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "super-secret-1", "display_name": "Дубль"},
    )
    assert again.status_code == 409


async def test_login_with_wrong_password_is_refused(client: AsyncClient, alice: dict) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "nope-nope-nope"}
    )
    assert response.status_code == 401


async def test_protected_routes_need_a_session(client: AsyncClient) -> None:
    assert (await client.get("/api/devices")).status_code == 401
    assert (await client.get("/api/state")).status_code == 401
    assert (await client.get("/api/dashboard")).status_code == 401


async def test_a_forged_token_is_refused(client: AsyncClient) -> None:
    forged = {"Authorization": "Bearer not-a-real-token"}
    assert (await client.get("/api/devices", headers=forged)).status_code == 401


async def test_state_returns_the_full_snapshot(client: AsyncClient, alice: dict) -> None:
    payload = (await client.get("/api/state", headers=auth(alice))).json()
    assert payload["esp_online"] is False
    assert payload["manual_override"] is False
    assert payload["automation"]["target_temperature"] == 22.0
    assert payload["devices"]
    assert payload["active_scenarios"] == []


async def test_device_is_created_and_listed(client: AsyncClient, alice: dict) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    assert created.status_code == 200
    assert created.json()["status"] == "SUCCESS"

    listed = await client.get("/api/devices", headers=auth(alice))
    assert "Лампа" in [device["name"] for device in listed.json()]


async def test_conflicting_channel_is_rejected(client: AsyncClient, alice: dict) -> None:
    await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    conflict = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Дубль", "type": "LIGHT", "physical_channel": 4},
    )
    assert conflict.status_code == 409


async def test_missing_device_returns_not_found(client: AsyncClient, alice: dict) -> None:
    assert (await client.get("/api/devices/999", headers=auth(alice))).status_code == 404


async def test_device_is_updated(client: AsyncClient, alice: dict) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    updated = await client.patch(
        f"/api/devices/{device_id}", headers=auth(alice), json={"name": "Люстра"}
    )
    assert updated.status_code == 200
    reloaded = await client.get(f"/api/devices/{device_id}", headers=auth(alice))
    assert reloaded.json()["name"] == "Люстра"


async def test_device_is_deleted(client: AsyncClient, alice: dict) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    deleted = await client.delete(f"/api/devices/{device_id}", headers=auth(alice))
    assert deleted.status_code == 200
    again = await client.delete(f"/api/devices/{device_id}", headers=auth(alice))
    assert again.status_code == 404


async def test_unknown_mode_is_rejected(client: AsyncClient, alice: dict) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    response = await client.post(
        f"/api/devices/{device_id}/mode", headers=auth(alice), json={"mode": "DANCE"}
    )
    assert response.status_code == 422


async def test_device_is_switched_on_through_the_api(
    client: AsyncClient, alice: dict, board
) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    response = await client.post(f"/api/devices/{device_id}/on", headers=auth(alice))
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert [command[1:] for command in board.commands] == [(4, True)]


async def test_offline_board_returns_service_unavailable(
    client: AsyncClient, alice: dict, board
) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    board.go_offline()
    response = await client.post(f"/api/devices/{device_id}/on", headers=auth(alice))
    assert response.status_code == 503


async def test_automation_settings_are_read_and_updated(client: AsyncClient, alice: dict) -> None:
    assert (await client.get("/api/automation", headers=auth(alice))).json()["enabled"] is False
    updated = await client.put("/api/automation", headers=auth(alice), json={"enabled": True})
    assert updated.json()["automation"]["enabled"] is True
    disabled = await client.post("/api/automation/disable", headers=auth(alice))
    assert disabled.json()["automation"]["enabled"] is False


async def test_automation_cycle_endpoint_reports_the_skip_reason(
    client: AsyncClient, alice: dict
) -> None:
    response = await client.post("/api/automation/run", headers=auth(alice))
    assert response.json()["message"] == "automation_disabled"


async def test_scenario_is_created_and_cancelled(client: AsyncClient, alice: dict) -> None:
    created = await client.post(
        "/api/scenarios",
        headers=auth(alice),
        json={"delay_minutes": 30, "target_temperature": 20.0, "capability": "COOL"},
    )
    scenario_id = created.json()["id"]
    listed = await client.get("/api/scenarios", headers=auth(alice))
    assert [item["id"] for item in listed.json()] == [scenario_id]
    cancelled = await client.delete(f"/api/scenarios/{scenario_id}", headers=auth(alice))
    assert cancelled.status_code == 200
    repeated = await client.delete(f"/api/scenarios/{scenario_id}", headers=auth(alice))
    assert repeated.status_code == 404


async def test_free_form_command_is_answered(client: AsyncClient, alice: dict, board) -> None:
    response = await client.post("/api/commands", headers=auth(alice), json={"text": "включи свет"})
    assert response.status_code == 200
    assert response.json()["intent"] == "TURN_ON"
    assert board.commands[-1][1:] == (1, True)


async def test_device_switch_publishes_a_realtime_event(
    client: AsyncClient, alice: dict, events
) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Лампа", "type": "LIGHT", "physical_channel": 4},
    )
    await client.post(f"/api/devices/{created.json()['data']['id']}/on", headers=auth(alice))
    assert "device.state_changed" in events.types()


async def test_preferences_round_trip(client: AsyncClient, alice: dict) -> None:
    assert (await client.get("/api/preferences", headers=auth(alice))).json()["theme"] == "dark"
    updated = await client.patch(
        "/api/preferences", headers=auth(alice), json={"temperature_unit": "F"}
    )
    assert updated.status_code == 200
    stored = await client.get("/api/preferences", headers=auth(alice))
    assert stored.json()["temperature_unit"] == "F"


async def test_preferences_reject_an_unknown_theme(client: AsyncClient, alice: dict) -> None:
    response = await client.patch("/api/preferences", headers=auth(alice), json={"theme": "neon"})
    assert response.status_code == 422


async def test_dashboard_is_personalized_per_account(
    client: AsyncClient, alice: dict, bob: dict
) -> None:
    layout = (await client.get("/api/dashboard", headers=auth(alice))).json()
    assert layout["widgets"][0]["type"] == "climate"
    renamed = await client.patch(
        "/api/dashboard",
        headers=auth(alice),
        json={
            "widgets": [
                {"type": "climate", "title": "Температура в спальне"},
                {"type": "device", "device_id": layout["widgets"][2]["device_id"]},
            ]
        },
    )
    assert renamed.status_code == 200
    updated = (await client.get("/api/dashboard", headers=auth(alice))).json()
    assert updated["widgets"][0]["title"] == "Температура в спальне"
    assert (await client.get("/api/dashboard", headers=auth(bob))).json()["widgets"][0].get(
        "title"
    ) is None


async def test_board_is_paired_and_reveals_its_key_once(client: AsyncClient, alice: dict) -> None:
    created = await client.post(
        "/api/esp-devices", headers=auth(alice), json={"name": "ESP кухня"}
    )
    assert created.status_code == 200
    key = created.json()["data"]["pairing_key"]
    assert key

    listed = await client.get("/api/esp-devices", headers=auth(alice))
    assert listed.json()[0]["online"] is False
    assert listed.json()[0]["pairing_key"] is None
    board_id = listed.json()[0]["id"]
    removed = await client.delete(f"/api/esp-devices/{board_id}", headers=auth(alice))
    assert removed.status_code == 200


async def test_two_accounts_never_see_each_other_devices(
    client: AsyncClient, alice: dict, bob: dict
) -> None:
    await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Секрет Алисы", "type": "LIGHT", "physical_channel": 4},
    )
    mine = await client.get("/api/devices", headers=auth(alice))
    theirs = await client.get("/api/devices", headers=auth(bob))
    alice_names = [device["name"] for device in mine.json()]
    bob_names = [device["name"] for device in theirs.json()]
    assert "Секрет Алисы" in alice_names
    assert "Секрет Алисы" not in bob_names


async def test_a_foreign_device_id_is_invisible_to_another_account(
    client: AsyncClient, alice: dict, bob: dict
) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Секрет Алисы", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    assert (await client.get(f"/api/devices/{device_id}", headers=auth(bob))).status_code == 404
    stolen = await client.patch(
        f"/api/devices/{device_id}", headers=auth(bob), json={"name": "Украдено"}
    )
    assert stolen.status_code == 404
    assert (await client.delete(f"/api/devices/{device_id}", headers=auth(bob))).status_code == 404
    still_there = await client.get(f"/api/devices/{device_id}", headers=auth(alice))
    assert still_there.json()["name"] == "Секрет Алисы"


async def test_a_device_of_another_account_is_never_switched(
    client: AsyncClient, alice: dict, bob: dict, board
) -> None:
    created = await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Секрет Алисы", "type": "LIGHT", "physical_channel": 4},
    )
    device_id = created.json()["data"]["id"]
    before = len(board.commands)
    assert (await client.post(f"/api/devices/{device_id}/on", headers=auth(bob))).status_code == 404
    assert len(board.commands) == before


async def test_two_accounts_may_use_the_same_relay_channel(
    client: AsyncClient, alice: dict, bob: dict
) -> None:
    for session, name in ((alice, "Лампа Алисы"), (bob, "Лампа Боба")):
        response = await client.post(
            "/api/devices",
            headers=auth(session),
            json={"name": name, "type": "LIGHT", "physical_channel": 4},
        )
        assert response.status_code == 200


async def test_automation_of_one_account_is_invisible_to_another(
    client: AsyncClient, alice: dict, bob: dict
) -> None:
    await client.put("/api/automation", headers=auth(alice), json={"enabled": True})
    assert (await client.get("/api/automation", headers=auth(bob))).json()["enabled"] is False


async def test_state_of_one_account_has_no_devices_of_another(
    client: AsyncClient, alice: dict, bob: dict
) -> None:
    await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Секрет Алисы", "type": "LIGHT", "physical_channel": 4},
    )
    snapshot = await client.get("/api/state", headers=auth(bob))
    assert "Секрет Алисы" not in [device["name"] for device in snapshot.json()["devices"]]


async def test_commands_only_reach_the_devices_of_the_session(
    client: AsyncClient, alice: dict, bob: dict, board
) -> None:
    await client.post(
        "/api/devices",
        headers=auth(alice),
        json={"name": "Секрет Алисы", "type": "LIGHT", "physical_channel": 4},
    )
    before = len(board.commands)
    response = await client.post(
        "/api/commands", headers=auth(bob), json={"text": "включи секрет алисы"}
    )
    assert response.status_code == 200
    assert len(board.commands) == before
