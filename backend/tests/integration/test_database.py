"""Tests of the database repositories."""

from __future__ import annotations

from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction
from smart_home_backend.domain.enums.device import Capability, DeviceType
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus

from tests.conftest import BASE_TIME


def make_device(channel: int, name: str = "Устройство") -> Device:
    return Device(
        id=0,
        name=name,
        type=DeviceType.OTHER,
        physical_channel=channel,
        capabilities=frozenset({Capability.ON, Capability.OFF}),
    )


async def test_device_is_stored_and_read_back(uow_factory) -> None:
    async with uow_factory() as uow:
        saved = await uow.devices.save(make_device(1, "Лампа"))
    async with uow_factory() as uow:
        stored = await uow.devices.get(saved.id)
    assert stored is not None
    assert stored.name == "Лампа"
    assert stored.capabilities == frozenset({Capability.ON, Capability.OFF})


async def test_device_is_updated_in_place(uow_factory) -> None:
    async with uow_factory() as uow:
        saved = await uow.devices.save(make_device(1))
        saved.name = "Люстра"
        await uow.devices.save(saved)
    async with uow_factory() as uow:
        stored = await uow.devices.get(saved.id)
    assert stored.name == "Люстра"


async def test_channel_conflict_is_detected(uow_factory) -> None:
    async with uow_factory() as uow:
        await uow.devices.save(make_device(1))
    async with uow_factory() as uow:
        assert await uow.devices.channel_in_use(1) is True
        assert await uow.devices.channel_in_use(2) is False


async def test_channel_can_be_reassigned_by_its_owner(uow_factory) -> None:
    async with uow_factory() as uow:
        first = await uow.devices.save(make_device(1))
    async with uow_factory() as uow:
        assert await uow.devices.channel_in_use(1, exclude_id=first.id) is False


async def test_device_is_found_by_channel(uow_factory) -> None:
    async with uow_factory() as uow:
        await uow.devices.save(make_device(3, "Вентилятор"))
    async with uow_factory() as uow:
        found = await uow.devices.get_by_channel(3)
    assert found is not None
    assert found.name == "Вентилятор"


async def test_deleting_a_missing_device_reports_false(uow_factory) -> None:
    async with uow_factory() as uow:
        assert await uow.devices.delete(999) is False


async def test_automation_defaults_are_created_on_first_read(uow_factory) -> None:
    async with uow_factory() as uow:
        settings = await uow.automation.get()
    assert settings.target_temperature == 22.0
    assert settings.enabled is False


async def test_automation_settings_survive_a_reload(uow_factory) -> None:
    async with uow_factory() as uow:
        settings = await uow.automation.get()
        settings.enabled = True
        settings.target_humidity = 55.0
        await uow.automation.save(settings)
    async with uow_factory() as uow:
        reloaded = await uow.automation.get()
    assert reloaded.enabled is True
    assert reloaded.target_humidity == 55.0


async def test_only_active_scenarios_are_listed(uow_factory) -> None:
    async with uow_factory() as uow:
        pending = await uow.scenarios.save(
            Scenario(
                id=0,
                status=ScenarioStatus.PENDING,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
                actions=[ScenarioAction(Capability.COOL, 20.0)],
                completion_behavior=CompletionBehavior.OFF,
            )
        )
        await uow.scenarios.save(
            Scenario(
                id=0,
                status=ScenarioStatus.COMPLETED,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
            )
        )
    async with uow_factory() as uow:
        active = await uow.scenarios.list_active()
        everything = await uow.scenarios.list_all()
    assert [scenario.id for scenario in active] == [pending.id]
    assert len(everything) == 2


async def test_scenario_snapshot_survives_a_reload(uow_factory) -> None:
    async with uow_factory() as uow:
        await uow.scenarios.save(
            Scenario(
                id=0,
                status=ScenarioStatus.RUNNING,
                created_at=BASE_TIME,
                start_at=BASE_TIME,
                restore_snapshot={1: "ON", 2: "COOL"},
            )
        )
    async with uow_factory() as uow:
        stored = (await uow.scenarios.list_all())[0]
    assert stored.restore_snapshot == {1: "ON", 2: "COOL"}
