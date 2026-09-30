"""Tests of the device executor."""

from __future__ import annotations

import pytest

from smart_home_backend.application.interface.services import CommandOutcome
from smart_home_backend.application.services import DeviceExecutor, HomeRuntime
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.operation import OperationStatus

from tests.conftest import FakeEspGateway


@pytest.fixture
def runtime(clock) -> HomeRuntime:
    state = HomeRuntime(clock)
    state.set_esp_online(True)
    return state


@pytest.fixture
def executor(esp: FakeEspGateway, runtime: HomeRuntime, events) -> DeviceExecutor:
    return DeviceExecutor(esp=esp, runtime=runtime, events=events)


async def test_switching_on_makes_the_relay_true(executor, light, esp: FakeEspGateway) -> None:
    result = await executor.apply(light, Capability.ON)
    assert result.status is OperationStatus.SUCCESS
    assert esp.commands == [(1, True)]


async def test_unsupported_capability_never_reaches_the_board(
    executor, light, esp: FakeEspGateway
) -> None:
    result = await executor.apply(light, Capability.COOL)
    assert result.status is OperationStatus.UNSUPPORTED
    assert esp.commands == []


async def test_offline_board_is_reported_as_unavailable(
    clock, events, light
) -> None:
    gateway = FakeEspGateway(CommandOutcome(ok=False, error="esp_offline"))
    runtime = HomeRuntime(clock)
    executor = DeviceExecutor(esp=gateway, runtime=runtime, events=events)
    result = await executor.apply(light, Capability.ON)
    assert result.status is OperationStatus.UNAVAILABLE


async def test_runtime_learns_the_cooling_mode(executor, air_conditioner, runtime) -> None:
    await executor.apply(air_conditioner, Capability.COOL)
    assert runtime.device_status(air_conditioner) is DeviceStatus.COOL


async def test_state_change_is_published(executor, light, events) -> None:
    await executor.apply(light, Capability.ON)
    assert events.types() == ["device.state_changed"]


async def test_apply_to_all_skips_incapable_devices(
    executor, light, air_conditioner, esp: FakeEspGateway
) -> None:
    results = await executor.apply_to_all([light, air_conditioner], Capability.ON)
    assert [result.device.id for result in results] == [1]


async def test_apply_first_matching_reports_unsupported(
    executor, light, esp: FakeEspGateway
) -> None:
    result = await executor.apply_first_matching([light], Capability.HEAT)
    assert result.status is OperationStatus.UNSUPPORTED
    assert esp.commands == []


async def test_restore_statuses_returns_devices_to_previous_state(
    executor, light, runtime
) -> None:
    results = await executor.restore_statuses([light], {light.id: DeviceStatus.OFF})
    assert results[0].status is OperationStatus.SUCCESS
    assert runtime.device_status(light) is DeviceStatus.OFF
