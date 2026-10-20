"""The state store keeps its promises about the state of a home.

Every operation of the adapter is a domain statement applied atomically by the
server, so the tests here exercise exactly those statements: measured values
keep whatever the sensor could not report, relay reports only move when a
position actually moved, a lost board forgets what its devices were doing, and
a device that stopped existing leaves no trace behind.
"""

from datetime import UTC, datetime, timedelta

from fakeredis import aioredis

from smart_home.domain.climate.climate_reading import ClimateReading
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.devices.relay_channel import RelayChannel
from smart_home.domain.devices.relay_state import RelayState
from smart_home.domain.identifiers import UserId
from smart_home.infrastructure.redis.state_store import RedisHomeStateStore
from tests.conftest import OWNER_UUID, make_device

NOW = datetime(2027, 5, 1, 12, 0, tzinfo=UTC)


def make_store() -> tuple[RedisHomeStateStore, str]:
    """Build a store over a fresh in-memory server.

    Args:
        None.

    Returns:
        tuple[RedisHomeStateStore, str]: The adapter and the prefix isolating it.
    """
    prefix = "tests"
    return RedisHomeStateStore(aioredis.FakeRedis(decode_responses=True), prefix), prefix


async def test_record_background_reading_keeps_absent_values():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)

    moved = await store.record_background_reading(user, ClimateReading.measured(21.4, 44.0), NOW)
    stored = await store.read(user)

    assert moved.temperature is not None and moved.temperature.celsius == 21.4
    assert moved.humidity is not None and moved.humidity.percent == 44.0
    assert stored.reading.temperature is not None and stored.reading.temperature.celsius == 21.4

    repeated = await store.record_background_reading(user, ClimateReading.measured(21.4, 44.0), NOW)
    assert repeated.temperature is None and repeated.humidity is None

    partial = await store.record_background_reading(user, ClimateReading.measured(22.0, None), NOW)
    kept = await store.read(user)

    assert partial.temperature is not None and partial.temperature.celsius == 22.0
    assert partial.humidity is None
    assert kept.reading.humidity is not None and kept.reading.humidity.percent == 44.0


async def test_record_relay_report_returns_only_moved_channels():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)

    first = await store.record_relay_report(user, [True, False], NOW)
    repeated = await store.record_relay_report(user, [True, False], NOW)
    moved = await store.record_relay_report(user, [False, True], NOW)

    assert first == (1,)
    assert repeated == ()
    assert moved == (1, 2)


async def test_record_command_result_writes_relay_and_device_memory():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    device = make_device()

    await store.record_command_result(user, device, DeviceStatus.ACTIVE, NOW)
    stored = await store.read(user)

    assert stored.relay_states[int(device.channel)] == RelayState.ON
    assert stored.device_modes[device.id] == DeviceStatus.ACTIVE


async def test_record_board_online_false_clears_device_memory():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    device = make_device()

    was_online = await store.record_board_online(user, True, NOW)
    await store.record_command_result(user, device, DeviceStatus.ACTIVE, NOW)
    went_away = await store.record_board_online(user, False, NOW)
    stored = await store.read(user)

    assert was_online is False
    assert went_away is True
    assert stored.board_online is False
    assert stored.device_modes == {}
    assert stored.relay_states[int(device.channel)] == RelayState.ON


async def test_forget_device_status_removes_only_one_device():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    device = make_device()
    other = make_device(name="Hallway lamp", channel=RelayChannel(5))

    await store.record_command_result(user, device, DeviceStatus.ACTIVE, NOW)
    await store.record_command_result(user, other, DeviceStatus.ACTIVE, NOW)
    await store.forget_device_status(user, device.id)
    stored = await store.read(user)

    assert device.id not in stored.device_modes
    assert stored.device_modes[other.id] == DeviceStatus.ACTIVE


async def test_set_override_until_ends_when_nobody_touches_it():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    until = NOW + timedelta(days=30)

    await store.set_override_until(user, until)
    held = await store.read(user)

    assert held.manual_override_until == until

    await store.set_override_until(user, None)
    released = await store.read(user)

    assert released.manual_override_until is None
