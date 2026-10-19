"""Tests of the use cases against a real database and a stubbed board.

Each test runs inside the scope of one registered account, which is how the
production code is always entered.
"""

from __future__ import annotations

import pytest

from smart_home_backend.application.dto.automation import UpdateAutomationCommand
from smart_home_backend.application.dto.command import ProcessUserCommand
from smart_home_backend.application.dto.device import CreateDeviceCommand, UpdateDeviceCommand
from smart_home_backend.application.dto.scenario import CreateScenarioCommand
from smart_home_backend.application.dto.user import AuthenticateUserCommand, RegisterUserCommand
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.user import DashboardWidget
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.domain.exceptions import (
    EmailAlreadyTakenError,
    InvalidCredentialsError,
)


@pytest.fixture
async def home(container, account) -> object:
    """Remove the starter devices so a test starts from an empty home.

    Args:
        container: Assembled dependency graph.
        account: Owner of the account.

    Returns:
        object: The dependency graph, ready to use.
    """
    for device in await container.get_devices.execute(account):
        await container.delete_device.execute(account, device.id)
    return container


@pytest.fixture
async def lamp(home, account) -> Device:
    return await create_device(home, account, "Лампа", "LIGHT", 1, ["ON", "OFF"])


@pytest.fixture
async def air_conditioner(home, account) -> Device:
    return await create_device(
        home, account, "Кондиционер", "AIR_CONDITIONER", 3, ["OFF", "COOL", "HEAT"]
    )


async def create_device(container, user_id, name, device_type, channel, capabilities) -> Device:
    status, device = await container.create_device.execute(
        user_id,
        CreateDeviceCommand(
            name=name, type=device_type, physical_channel=channel, capabilities=capabilities
        ),
    )
    assert status is OperationStatus.SUCCESS
    return device


async def test_registration_creates_an_account_with_its_own_uuid(container) -> None:
    session = await container.register_user.execute(
        RegisterUserCommand(email="a@b.com", password="super-secret-1", display_name="А")
    )
    assert str(session.user_id)
    assert session.token
    assert session.user.login == "a@b.com"


async def test_login_of_an_unknown_account_is_refused(container) -> None:
    with pytest.raises(InvalidCredentialsError):
        await container.authenticate_user.execute(
            AuthenticateUserCommand(email="nobody@example.com", password="whatever-1")
        )


async def test_login_with_a_wrong_password_is_refused(container, account) -> None:
    with pytest.raises(InvalidCredentialsError):
        await container.authenticate_user.execute(
            AuthenticateUserCommand(email="vasya@example.com", password="wrong-password")
        )


async def test_registration_of_a_taken_login_is_refused(container, account) -> None:
    with pytest.raises(EmailAlreadyTakenError):
        await container.register_user.execute(
            RegisterUserCommand(
                email="vasya@example.com", password="super-secret-1", display_name="Дубль"
            )
        )


async def test_device_is_created(home, account) -> None:
    status, device = await home.create_device.execute(
        account, CreateDeviceCommand(name="Лампа", type="LIGHT", physical_channel=1)
    )
    assert status is OperationStatus.SUCCESS
    assert device.name == "Лампа"


async def test_second_device_on_the_same_channel_is_rejected(home, lamp, account) -> None:
    status, device = await home.create_device.execute(
        account, CreateDeviceCommand(name="Дубль", type="LIGHT", physical_channel=1)
    )
    assert status is OperationStatus.CHANNEL_CONFLICT
    assert device is None


async def test_device_is_renamed_and_retyped(home, lamp, account) -> None:
    status, updated = await home.update_device.execute(
        account, lamp.id, UpdateDeviceCommand(name="Люстра", type="OTHER")
    )
    assert status is OperationStatus.SUCCESS
    assert updated.name == "Люстра"
    assert updated.type.value == "OTHER"


async def test_updating_a_missing_device_reports_not_found(home, account) -> None:
    status, device = await home.update_device.execute(
        account, 42, UpdateDeviceCommand(name="x")
    )
    assert status is OperationStatus.NOT_FOUND
    assert device is None


async def test_device_is_deleted(home, lamp, account) -> None:
    assert await home.delete_device.execute(account, lamp.id) is OperationStatus.SUCCESS
    assert await home.delete_device.execute(account, lamp.id) is OperationStatus.NOT_FOUND


async def test_device_command_reaches_the_board(home, lamp, account, board) -> None:
    result = await home.turn_device_on.execute(account, lamp.id)
    assert result.status is OperationStatus.SUCCESS
    assert board.commands == [(account, 1, True)]


async def test_missing_device_command_reports_not_found(home, account) -> None:
    result = await home.turn_device_off.execute(account, 404)
    assert result.status is OperationStatus.NOT_FOUND


async def test_manual_command_suspends_automation(home, lamp, account) -> None:
    await home.turn_device_on.execute(account, lamp.id)
    assert home.runtimes.for_user(account).is_manual_override() is True


async def test_switch_all_reports_switched_devices(
    home, lamp, air_conditioner, account, board
) -> None:
    result = await home.turn_all_devices.execute(account, False)
    assert sorted(channel for _user, channel, _on in board.commands) == [1, 3]
    assert len(result.switched) == 2


async def test_offline_board_is_reported_to_the_user(home, lamp, account, board) -> None:
    board.go_offline()
    result = await home.turn_device_on.execute(account, lamp.id)
    assert result.status is OperationStatus.UNAVAILABLE


async def test_device_command_fails_without_support(home, account, board) -> None:
    heater = await create_device(home, account, "Обогреватель", "HEATER", 5, ["ON", "OFF"])
    result = await home.set_device_mode.execute(account, heater.id, Capability.COOL)
    assert result.status is OperationStatus.UNSUPPORTED
    assert board.commands == []


async def test_mode_command_switches_into_cooling(
    home, air_conditioner, account, board
) -> None:
    result = await home.set_device_mode.execute(account, air_conditioner.id, Capability.COOL)
    assert result.status is OperationStatus.SUCCESS
    assert board.commands == [(account, 3, True)]
    assert home.runtimes.for_user(account).device_status(air_conditioner) is DeviceStatus.COOL


async def test_automation_settings_round_trip(home, account) -> None:
    await home.update_automation.execute(
        account, UpdateAutomationCommand(enabled=True, target_temperature=21.5)
    )
    settings = await home.get_automation_settings.execute(account)
    assert settings.enabled is True
    assert settings.target_temperature == 21.5


async def test_temperature_target_is_validated(home, account) -> None:
    status, _settings = await home.set_target_temperature.execute(account, 90.0)
    assert status is OperationStatus.INVALID_INPUT


async def test_humidity_target_is_validated(home, account) -> None:
    status, _settings = await home.set_target_humidity.execute(account, 140.0)
    assert status is OperationStatus.INVALID_INPUT


async def test_automation_cycle_uses_the_target_range(
    home, air_conditioner, account, board
) -> None:
    await home.update_automation.execute(
        account,
        UpdateAutomationCommand(enabled=True, target_temperature=22.0, temperature_tolerance=1.0),
    )
    home.runtimes.for_user(account).apply_reading(26.0, 40.0)
    cycle = await home.run_automation_cycle.execute(account)
    assert cycle.demands == ["COOL"]
    assert board.commands == [(account, 3, True)]


async def test_automation_cycle_changes_nothing_inside_the_range(
    home, air_conditioner, account, board
) -> None:
    await home.update_automation.execute(
        account,
        UpdateAutomationCommand(enabled=True, target_temperature=22.0, temperature_tolerance=1.0),
    )
    home.runtimes.for_user(account).apply_reading(22.3, 45.0)
    cycle = await home.run_automation_cycle.execute(account)
    assert cycle.demands == []
    assert board.commands == []


async def test_scenario_is_created_and_listed(home, account) -> None:
    scenario = await home.create_scenario.execute(
        account,
        CreateScenarioCommand(
            delay_minutes=30,
            target_temperature=20.0,
            capability=Capability.COOL,
            target="room",
        ),
    )
    active = await home.get_active_scenarios.execute(account)
    assert [item.id for item in active] == [scenario.id]


async def test_scenario_is_cancelled(home, account) -> None:
    scenario = await home.create_scenario.execute(
        account, CreateScenarioCommand(delay_minutes=10)
    )
    status, cancelled = await home.cancel_scenario.execute(account, scenario.id)
    assert status is OperationStatus.SUCCESS
    assert cancelled.status.value == "CANCELLED"


async def test_cancelling_twice_reports_not_found(home, account) -> None:
    scenario = await home.create_scenario.execute(
        account, CreateScenarioCommand(delay_minutes=10)
    )
    await home.cancel_scenario.execute(account, scenario.id)
    status, _scenario = await home.cancel_scenario.execute(account, scenario.id)
    assert status is OperationStatus.NOT_FOUND


async def test_cancelling_a_missing_scenario(home, account) -> None:
    status, scenario = await home.cancel_scenario.execute(account, 999)
    assert status is OperationStatus.NOT_FOUND
    assert scenario is None


async def test_home_snapshot_reports_the_board_state(home, lamp, account) -> None:
    snapshot = await home.get_home_snapshot.execute(account)
    assert snapshot.esp_online is True
    assert snapshot.automation.target_temperature == 22.0


async def test_devices_query_returns_every_device(home, account) -> None:
    await create_device(home, account, "Лампа", "LIGHT", 1, ["ON", "OFF"])
    await create_device(home, account, "Люстра", "LIGHT", 2, ["ON", "OFF"])
    assert len(await home.get_devices.execute(account)) == 2


async def test_free_form_command_switches_the_light_on(home, lamp, account, board) -> None:
    result = await home.process_user_command.execute(
        account, ProcessUserCommand(text="включи свет")
    )
    assert result.ok is True
    assert board.commands == [(account, 1, True)]


async def test_free_form_command_reports_a_missing_device(home, account, board) -> None:
    result = await home.process_user_command.execute(
        account, ProcessUserCommand(text="включи чайник")
    )
    assert result.ok is False
    assert board.commands == []


async def test_scenario_tick_starts_a_due_scenario(
    home, air_conditioner, account, board
) -> None:
    scenario = await home.create_scenario.execute(
        account, CreateScenarioCommand(delay_minutes=0, capability=Capability.COOL)
    )
    await home.tick_scenarios.execute(account)
    active = await home.get_active_scenarios.execute(account)
    assert scenario.id in [item.id for item in active]
    assert board.commands == [(account, 3, True)]


async def test_dashboard_rejects_a_widget_of_another_account(home, account, container) -> None:
    from smart_home_backend.application.dto.user import UpdateDashboardCommand

    other = await container.register_user.execute(
        RegisterUserCommand(
            email="other@example.com", password="super-secret-1", display_name="Другой"
        )
    )
    foreign_device = (await container.get_devices.execute(other.user_id))[0]
    status, _dashboard = await home.update_dashboard.execute(
        account,
        UpdateDashboardCommand(
            widgets=[DashboardWidget(type="device", device_id=foreign_device.id)]
        ),
    )
    assert status is OperationStatus.INVALID_INPUT


async def test_preferences_reject_an_unknown_value(home, account) -> None:
    from smart_home_backend.application.dto.user import UpdatePreferencesCommand

    status, _preferences = await home.update_preferences.execute(
        account, UpdatePreferencesCommand(theme="neon")
    )
    assert status is OperationStatus.INVALID_INPUT


async def test_two_accounts_keep_their_own_devices(home, account, container) -> None:
    other = await container.register_user.execute(
        RegisterUserCommand(
            email="second@example.com", password="super-secret-1", display_name="Второй"
        )
    )
    await create_device(home, account, "Только моя", "LIGHT", 1, ["ON", "OFF"])
    assert [device.name for device in await home.get_devices.execute(account)] == ["Только моя"]
    assert [device.name for device in await home.get_devices.execute(other.user_id)] != [
        "Только моя"
    ]
