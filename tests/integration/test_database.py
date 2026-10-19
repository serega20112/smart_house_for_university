"""Tests of the database repositories.

Every test registers two owners, because the interesting question is never
whether a repository works but whether it can be made to leak across accounts.
"""

from __future__ import annotations

import pytest

from smart_home_backend.application.dto.user import RegisterUserCommand
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction
from smart_home_backend.domain.entities.user import User
from smart_home_backend.domain.enums.device import Capability, DeviceType
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus
from smart_home_backend.domain.policies import PasswordPolicy
from smart_home_backend.domain.value_objects.identity import UserId
from tests.conftest import BASE_TIME


async def register(uow_factory, email: str) -> UserId:
    """Create an account directly through the unit of work.

    Args:
        uow_factory: Factory producing units of work.
        email: Login of the new account.

    Returns:
        UserId: Identifier of the created account.
    """
    user_id = UserId.generate()
    async with uow_factory() as uow:
        await uow.users.add(
            User(
                id=user_id,
                email=email,
                password_hash=PasswordPolicy.hash("super-secret-1"),
                display_name=email,
                created_at=BASE_TIME,
            )
        )
    return user_id


@pytest.fixture
async def alice(uow_factory) -> UserId:
    return await register(uow_factory, "alice@example.com")


@pytest.fixture
async def bob(uow_factory) -> UserId:
    return await register(uow_factory, "bob@example.com")


def make_device(channel: int, name: str = "Устройство") -> Device:
    return Device(
        id=0,
        name=name,
        type=DeviceType.OTHER,
        physical_channel=channel,
        capabilities=frozenset({Capability.ON, Capability.OFF}),
    )


async def test_device_is_stored_and_read_back(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        saved = await uow.devices.save(alice, make_device(1, "Лампа"))
    async with uow_factory() as uow:
        stored = await uow.devices.get(alice, saved.id)
    assert stored is not None
    assert stored.name == "Лампа"
    assert stored.capabilities == frozenset({Capability.ON, Capability.OFF})


async def test_device_is_updated_in_place(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        saved = await uow.devices.save(alice, make_device(1))
        saved.name = "Люстра"
        await uow.devices.save(alice, saved)
    async with uow_factory() as uow:
        stored = await uow.devices.get(alice, saved.id)
    assert stored.name == "Люстра"


async def test_channel_conflict_is_detected(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        await uow.devices.save(alice, make_device(1))
    async with uow_factory() as uow:
        assert await uow.devices.channel_in_use(alice, 1) is True
        assert await uow.devices.channel_in_use(alice, 2) is False


async def test_channel_can_be_reassigned_by_its_owner(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        first = await uow.devices.save(alice, make_device(1))
    async with uow_factory() as uow:
        assert await uow.devices.channel_in_use(alice, 1, exclude_id=first.id) is False


async def test_device_is_found_by_channel(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        await uow.devices.save(alice, make_device(3, "Вентилятор"))
    async with uow_factory() as uow:
        found = await uow.devices.get_by_channel(alice, 3)
    assert found is not None
    assert found.name == "Вентилятор"


async def test_deleting_a_missing_device_reports_false(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        assert await uow.devices.delete(alice, 999) is False


async def test_a_device_of_another_account_is_invisible(uow_factory, alice, bob) -> None:
    async with uow_factory() as uow:
        saved = await uow.devices.save(alice, make_device(1, "Лампа"))
    async with uow_factory() as uow:
        assert await uow.devices.get(bob, saved.id) is None
        assert await uow.devices.get_by_channel(bob, 1) is None
        assert list(await uow.devices.list_all(bob)) == []
        assert await uow.devices.delete(bob, saved.id) is False


async def test_two_accounts_may_use_the_same_channel(uow_factory, alice, bob) -> None:
    async with uow_factory() as uow:
        await uow.devices.save(alice, make_device(1, "Лампа Алисы"))
    async with uow_factory() as uow:
        await uow.devices.save(bob, make_device(1, "Лампа Боба"))
    async with uow_factory() as uow:
        assert await uow.devices.channel_in_use(alice, 1) is True
        assert await uow.devices.channel_in_use(bob, 1) is True


async def test_automation_defaults_are_created_on_first_read(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        settings = await uow.automation.get(alice)
    assert settings.target_temperature == 22.0
    assert settings.enabled is False


async def test_automation_settings_survive_a_reload(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        settings = await uow.automation.get(alice)
        settings.enabled = True
        settings.target_humidity = 55.0
        await uow.automation.save(alice, settings)
    async with uow_factory() as uow:
        reloaded = await uow.automation.get(alice)
    assert reloaded.enabled is True
    assert reloaded.target_humidity == 55.0


async def test_automation_settings_are_not_shared(uow_factory, alice, bob) -> None:
    async with uow_factory() as uow:
        settings = await uow.automation.get(alice)
        settings.enabled = True
        await uow.automation.save(alice, settings)
    async with uow_factory() as uow:
        assert (await uow.automation.get(bob)).enabled is False


async def test_only_active_scenarios_are_listed(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        pending = await uow.scenarios.save(
            alice,
            Scenario(
                id=0,
                status=ScenarioStatus.PENDING,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
                actions=[ScenarioAction(Capability.COOL, 20.0)],
                completion_behavior=CompletionBehavior.OFF,
            ),
        )
        await uow.scenarios.save(
            alice,
            Scenario(
                id=0,
                status=ScenarioStatus.COMPLETED,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
            ),
        )
    async with uow_factory() as uow:
        active = await uow.scenarios.list_active(alice)
        everything = await uow.scenarios.list_all(alice)
    assert [scenario.id for scenario in active] == [pending.id]
    assert len(everything) == 2


async def test_scenario_snapshot_survives_a_reload(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        await uow.scenarios.save(
            alice,
            Scenario(
                id=0,
                status=ScenarioStatus.RUNNING,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
                restore_snapshot={1: "ON", 2: "COOL"},
            ),
        )
    async with uow_factory() as uow:
        stored = (await uow.scenarios.list_all(alice))[0]
    assert stored.restore_snapshot == {1: "ON", 2: "COOL"}


async def test_a_scenario_of_another_account_is_invisible(uow_factory, alice, bob) -> None:
    async with uow_factory() as uow:
        saved = await uow.scenarios.save(
            alice,
            Scenario(
                id=0,
                status=ScenarioStatus.PENDING,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
            ),
        )
    async with uow_factory() as uow:
        assert await uow.scenarios.get(bob, saved.id) is None
        assert list(await uow.scenarios.list_active(bob)) == []
        assert await uow.scenarios.delete(bob, saved.id) is False


async def test_preferences_are_created_on_first_read(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        preferences = await uow.preferences.get(alice)
    assert preferences.temperature_unit == "C"
    assert preferences.user_id == alice


async def test_dashboard_is_created_on_first_read(uow_factory, alice) -> None:
    async with uow_factory() as uow:
        dashboard = await uow.dashboard.get(alice)
    assert dashboard.widgets == ()
    assert dashboard.user_id == alice


async def test_register_use_case_seeds_a_complete_home(container) -> None:
    session = await container.register_user.execute(
        RegisterUserCommand(
            email="newcomer@example.com",
            password="super-secret-1",
            display_name="Новичок",
        )
    )
    devices = await container.get_devices.execute(session.user_id)
    dashboard = await container.get_dashboard.execute(session.user_id)
    assert devices
    assert [widget.type for widget in dashboard.widgets][:2] == ["climate", "command"]


async def test_a_login_is_never_returned_by_another_repository(uow_factory) -> None:
    user_id = await register(uow_factory, "unique@example.com")
    async with uow_factory() as uow:
        assert await uow.users.get_by_email("UNIQUE@example.com") is not None
        assert (await uow.users.get(user_id)).email == "unique@example.com"
