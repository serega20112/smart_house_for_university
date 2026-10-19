"""Tests of the device executor."""

from __future__ import annotations

import pytest

from smart_home_backend.application.interface.services import CommandOutcome
from smart_home_backend.application.services import DeviceExecutor, HomeRuntime, HomeRuntimes
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.operation import OperationStatus
from tests.conftest import FakeEspGateway


@pytest.fixture
def runtimes(clock, owner) -> HomeRuntimes:
    registry = HomeRuntimes(clock)
    registry.for_user(owner).set_esp_online(True)
    return registry


@pytest.fixture
def runtime(runtimes: HomeRuntimes, owner) -> HomeRuntime:
    return runtimes.for_user(owner)


@pytest.fixture
def executor(esp: FakeEspGateway, runtimes: HomeRuntimes, events) -> DeviceExecutor:
    return DeviceExecutor(esp=esp, runtimes=runtimes, events=events)


async def test_switching_on_makes_the_relay_true(
    executor, light, esp: FakeEspGateway, owner
) -> None:
    result = await executor.apply(owner, light, Capability.ON)
    assert result.status is OperationStatus.SUCCESS
    assert esp.commands == [(owner, 1, True)]


async def test_unsupported_capability_never_reaches_the_board(
    executor, light, esp: FakeEspGateway, owner
) -> None:
    result = await executor.apply(owner, light, Capability.COOL)
    assert result.status is OperationStatus.UNSUPPORTED
    assert esp.commands == []


async def test_offline_board_is_reported_as_unavailable(clock, events, light, owner) -> None:
    gateway = FakeEspGateway(CommandOutcome(ok=False, error="esp_offline"))
    executor = DeviceExecutor(esp=gateway, runtimes=HomeRuntimes(clock), events=events)
    result = await executor.apply(owner, light, Capability.ON)
    assert result.status is OperationStatus.UNAVAILABLE


async def test_runtime_learns_the_cooling_mode(
    executor, air_conditioner, runtime, owner
) -> None:
    await executor.apply(owner, air_conditioner, Capability.COOL)
    assert runtime.device_status(air_conditioner) is DeviceStatus.COOL


async def test_state_change_is_published(executor, light, events, owner) -> None:
    await executor.apply(owner, light, Capability.ON)
    assert events.types() == ["device.state_changed"]


async def test_apply_to_all_skips_incapable_devices(
    executor, light, air_conditioner, esp: FakeEspGateway, owner
) -> None:
    results = await executor.apply_to_all(owner, [light, air_conditioner], Capability.ON)
    assert [result.device.id for result in results] == [1]


async def test_apply_first_matching_reports_unsupported(
    executor, light, esp: FakeEspGateway, owner
) -> None:
    result = await executor.apply_first_matching(owner, [light], Capability.HEAT)
    assert result.status is OperationStatus.UNSUPPORTED
    assert esp.commands == []


async def test_restore_statuses_returns_devices_to_previous_state(
    executor, light, runtime, owner
) -> None:
    results = await executor.restore_statuses(owner, [light], {light.id: DeviceStatus.OFF})
    assert results[0].status is OperationStatus.SUCCESS
    assert runtime.device_status(light) is DeviceStatus.OFF


async def test_two_users_never_share_a_board(
    executor, light, esp: FakeEspGateway, owner, other_owner
) -> None:
    await executor.apply(owner, light, Capability.ON)
    await executor.apply(other_owner, light, Capability.OFF)
    assert [command[0] for command in esp.commands] == [owner, other_owner]


async def test_events_carry_the_owner(executor, light, events, owner, other_owner) -> None:
    await executor.apply(owner, light, Capability.ON)
    assert events.types_for(other_owner) == []
