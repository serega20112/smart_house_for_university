"""Tests of the use cases against a real database and a stubbed board."""

from __future__ import annotations

import pytest

from smart_home_backend.application.dto.automation import UpdateAutomationCommand
from smart_home_backend.application.dto.command import ProcessUserCommand
from smart_home_backend.application.dto.device import CreateDeviceCommand, UpdateDeviceCommand
from smart_home_backend.application.dto.scenario import CreateScenarioCommand
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.operation import OperationStatus


@pytest.fixture
async def lamp(container) -> Device:
    return await create_device(container, "Лампа", "LIGHT", 1, ["ON", "OFF"])


@pytest.fixture
async def air_conditioner(container) -> Device:
    return await create_device(
        container, "Кондиционер", "AIR_CONDITIONER", 3, ["OFF", "COOL", "HEAT"]
    )


async def create_device(
    container, name: str, device_type: str, channel: int, capabilities: list[str]
) -> Device:
    status, device = await container.create_device.execute(
        CreateDeviceCommand(
            name=name, type=device_type, physical_channel=channel, capabilities=capabilities
        )
    )
    assert status is OperationStatus.SUCCESS
    return device


async def test_device_is_created(container) -> None:
    status, device = await container.create_device.execute(
        CreateDeviceCommand(name="Лампа", type="LIGHT", physical_channel=1)
    )
    assert status is OperationStatus.SUCCESS
    assert device.name == "Лампа"


async def test_second_device_on_the_same_channel_is_rejected(container, lamp) -> None:
    status, device = await container.create_device.execute(
        CreateDeviceCommand(name="Дубль", type="LIGHT", physical_channel=1)
    )
    assert status is OperationStatus.CHANNEL_CONFLICT
    assert device is None


async def test_device_is_renamed_and_retyped(container, lamp) -> None:
    status, updated = await container.update_device.execute(
        lamp.id, UpdateDeviceCommand(name="Люстра", type="OTHER")
    )
    assert status is OperationStatus.SUCCESS
    assert updated.name == "Люстра"
    assert updated.type.value == "OTHER"


async def test_updating_a_missing_device_reports_not_found(container) -> None:
    status, device = await container.update_device.execute(42, UpdateDeviceCommand(name="x"))
    assert status is OperationStatus.NOT_FOUND
    assert device is None


async def test_device_is_deleted(container, lamp) -> None:
    assert await container.delete_device.execute(lamp.id) is OperationStatus.SUCCESS
    assert await container.delete_device.execute(lamp.id) is OperationStatus.NOT_FOUND


async def test_device_command_reaches_the_board(container, lamp, board) -> None:
    result = await container.turn_device_on.execute(lamp.id)
    assert result.status is OperationStatus.SUCCESS
    assert board.commands == [(1, True)]


async def test_missing_device_command_reports_not_found(container) -> None:
    result = await container.turn_device_off.execute(404)
    assert result.status is OperationStatus.NOT_FOUND


async def test_manual_command_suspends_automation(container, lamp) -> None:
    await container.turn_device_on.execute(lamp.id)
    assert container.runtime.is_manual_override() is True


async def test_switch_all_reports_switched_devices(
    container, lamp, air_conditioner, board
) -> None:
    result = await container.turn_all_devices.execute(False)
    assert sorted(channel for channel, _on in board.commands) == [1, 3]
    assert len(result.switched) == 2


async def test_offline_board_is_reported_to_the_user(container, lamp, board) -> None:
    board.go_offline()
    result = await container.turn_device_on.execute(lamp.id)
    assert result.status is OperationStatus.UNAVAILABLE


async def test_device_command_fails_without_support(container, board) -> None:
    heater = await create_device(container, "Обогреватель", "HEATER", 5, ["ON", "OFF"])
    result = await container.set_device_mode.execute(heater.id, Capability.COOL)
    assert result.status is OperationStatus.UNSUPPORTED
    assert board.commands == []


async def test_mode_command_switches_into_cooling(container, air_conditioner, board) -> None:
    result = await container.set_device_mode.execute(air_conditioner.id, Capability.COOL)
    assert result.status is OperationStatus.SUCCESS
    assert board.commands == [(3, True)]
    assert container.runtime.device_status(air_conditioner) is DeviceStatus.COOL


async def test_automation_settings_round_trip(container) -> None:
    await container.update_automation.execute(
        UpdateAutomationCommand(enabled=True, target_temperature=21.5)
    )
    settings = await container.get_automation_settings.execute()
    assert settings.enabled is True
    assert settings.target_temperature == 21.5


async def test_temperature_target_is_validated(container) -> None:
    status, _settings = await container.set_target_temperature.execute(90.0)
    assert status is OperationStatus.INVALID_INPUT


async def test_humidity_target_is_validated(container) -> None:
    status, _settings = await container.set_target_humidity.execute(140.0)
    assert status is OperationStatus.INVALID_INPUT


async def test_automation_cycle_uses_the_target_range(container, air_conditioner, board) -> None:
    await container.update_automation.execute(
        UpdateAutomationCommand(enabled=True, target_temperature=22.0, temperature_tolerance=1.0)
    )
    container.runtime.apply_reading(26.0, 40.0)
    cycle = await container.run_automation_cycle.execute()
    assert cycle.demands == ["COOL"]
    assert board.commands == [(3, True)]


async def test_automation_cycle_changes_nothing_inside_the_range(
    container, air_conditioner, board
) -> None:
    await container.update_automation.execute(
        UpdateAutomationCommand(enabled=True, target_temperature=22.0, temperature_tolerance=1.0)
    )
    container.runtime.apply_reading(22.3, 45.0)
    cycle = await container.run_automation_cycle.execute()
    assert cycle.demands == []
    assert board.commands == []


async def test_scenario_is_created_and_listed(container) -> None:
    scenario = await container.create_scenario.execute(
        CreateScenarioCommand(
            delay_minutes=30,
            target_temperature=20.0,
            capability=Capability.COOL,
            target="room",
        )
    )
    active = await container.get_active_scenarios.execute()
    assert [item.id for item in active] == [scenario.id]


async def test_scenario_is_cancelled(container) -> None:
    scenario = await container.create_scenario.execute(CreateScenarioCommand(delay_minutes=10))
    status, cancelled = await container.cancel_scenario.execute(scenario.id)
    assert status is OperationStatus.SUCCESS
    assert cancelled.status.value == "CANCELLED"


async def test_cancelling_twice_reports_not_found(container) -> None:
    scenario = await container.create_scenario.execute(CreateScenarioCommand(delay_minutes=10))
    await container.cancel_scenario.execute(scenario.id)
    status, _scenario = await container.cancel_scenario.execute(scenario.id)
    assert status is OperationStatus.NOT_FOUND


async def test_cancelling_a_missing_scenario(container) -> None:
    status, scenario = await container.cancel_scenario.execute(999)
    assert status is OperationStatus.NOT_FOUND
    assert scenario is None


async def test_home_snapshot_reports_the_board_state(container, lamp) -> None:
    snapshot = await container.get_home_snapshot.execute()
    assert snapshot.esp_online is True
    assert snapshot.automation.target_temperature == 22.0


async def test_devices_query_returns_every_device(container) -> None:
    await create_device(container, "Лампа", "LIGHT", 1, ["ON", "OFF"])
    await create_device(container, "Люстра", "LIGHT", 2, ["ON", "OFF"])
    assert len(await container.get_devices.execute()) == 2


async def test_free_form_command_switches_the_light_on(container, lamp, board) -> None:
    result = await container.process_user_command.execute(
        ProcessUserCommand(text="включи свет")
    )
    assert result.ok is True
    assert board.commands == [(1, True)]


async def test_free_form_command_reports_a_missing_device(container, board) -> None:
    result = await container.process_user_command.execute(
        ProcessUserCommand(text="включи чайник")
    )
    assert result.ok is False
    assert board.commands == []


async def test_scenario_tick_starts_a_due_scenario(container, air_conditioner, board) -> None:
    scenario = await container.create_scenario.execute(
        CreateScenarioCommand(delay_minutes=0, capability=Capability.COOL)
    )
    await container.tick_scenarios.execute()
    active = await container.get_active_scenarios.execute()
    assert scenario.id in [item.id for item in active]
    assert board.commands == [(3, True)]
