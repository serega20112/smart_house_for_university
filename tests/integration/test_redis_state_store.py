"""The state store keeps its promises about the state of a home.

Every operation of the adapter is a domain statement applied atomically by the
server, so the tests here exercise exactly those statements: measured values
keep whatever the sensor could not report, relay reports only move when a
position actually moved, boards keep their own channels and sensors, a lost
board leaves its neighbours available, and a device that stopped existing leaves
no trace behind.
"""

from datetime import UTC, datetime, timedelta

from fakeredis import aioredis

from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_channel import RelayChannel
from backend.domain.value_objects.devices.relay_state import RelayState
from backend.infrastructure.brokers import keys
from backend.infrastructure.brokers.state_schema import STATE_VERSION
from backend.infrastructure.brokers.state_store import RedisHomeStateStore
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


def two_boards() -> tuple[EspDeviceId, EspDeviceId]:
    """Name two boards of one home.

    Returns:
        tuple[EspDeviceId, EspDeviceId]: The boards every test talks to.
    """
    return EspDeviceId.generate(), EspDeviceId.generate()


async def test_record_background_reading_keeps_absent_values():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    board, _other = two_boards()

    moved = await store.record_background_reading(
        user, board, ClimateReading.measured(21.4, 44.0), NOW
    )
    stored = await store.read(user)

    assert moved.temperature is not None and moved.temperature.celsius == 21.4
    assert moved.humidity is not None and moved.humidity.percent == 44.0
    assert stored.reading.temperature is not None and stored.reading.temperature.celsius == 21.4

    repeated = await store.record_background_reading(
        user, board, ClimateReading.measured(21.4, 44.0), NOW
    )
    assert repeated.temperature is None and repeated.humidity is None

    partial = await store.record_background_reading(
        user, board, ClimateReading.measured(22.0, None), NOW
    )
    kept = await store.read(user)

    assert partial.temperature is not None and partial.temperature.celsius == 22.0
    assert partial.humidity is None
    assert kept.reading.humidity is not None and kept.reading.humidity.percent == 44.0


async def test_two_boards_keep_their_own_sensors():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    living_room, garage = two_boards()

    await store.record_background_reading(
        user, living_room, ClimateReading.measured(21.4, 44.0), NOW
    )
    await store.record_background_reading(user, garage, ClimateReading.measured(9.0, None), NOW)
    stored = await store.read(user)

    living_temperature = stored.readings[living_room].temperature
    garage_temperature = stored.readings[garage].temperature
    assert living_temperature is not None and living_temperature.celsius == 21.4
    assert garage_temperature is not None and garage_temperature.celsius == 9.0
    assert stored.reading.temperature is not None and stored.reading.temperature.celsius == 9.0


async def test_record_relay_report_returns_only_moved_channels():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    board, _other = two_boards()

    first = await store.record_relay_report(user, board, [True, False], NOW)
    repeated = await store.record_relay_report(user, board, [True, False], NOW)
    moved = await store.record_relay_report(user, board, [False, True], NOW)

    assert first == (1,)
    assert repeated == ()
    assert moved == (1, 2)


async def test_two_boards_do_not_share_a_channel():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    living_room, garage = two_boards()

    await store.record_relay_report(user, living_room, [True], NOW)
    moved = await store.record_relay_report(user, garage, [False], NOW)
    stored = await store.read(user)

    assert moved == ()
    assert stored.is_relay_closed(living_room, 1)
    assert not stored.is_relay_closed(garage, 1)


async def test_record_command_result_writes_relay_and_device_memory():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    board, _other = two_boards()
    device = make_device(board_id=board)

    await store.record_command_result(
        user, board, device.id, int(device.channel), DeviceStatus.ACTIVE, NOW
    )
    stored = await store.read(user)

    assert stored.relay_states[board][int(device.channel)] is RelayState.ON
    assert stored.device_modes[device.id] == DeviceStatus.ACTIVE


async def test_losing_one_board_keeps_the_other_available():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    living_room, garage = two_boards()
    device = make_device(board_id=living_room)

    first_was_online = await store.record_board_online(user, living_room, True, NOW)
    await store.record_board_online(user, garage, True, NOW)
    await store.record_command_result(
        user, living_room, device.id, int(device.channel), DeviceStatus.ACTIVE, NOW
    )
    went_away = await store.record_board_online(user, living_room, False, NOW)
    stored = await store.read(user)

    assert first_was_online is False
    assert went_away is True
    assert stored.online_boards == frozenset({garage})
    assert stored.board_online is True
    assert stored.status_of(device) is DeviceStatus.UNAVAILABLE
    assert stored.device_modes[device.id] == DeviceStatus.ACTIVE


async def test_forget_device_status_removes_only_one_device():
    store, _prefix = make_store()
    user = UserId.parse(OWNER_UUID)
    board, _other = two_boards()
    device = make_device(board_id=board)
    other = make_device(name="Hallway lamp", channel=RelayChannel(5), board_id=board)

    await store.record_command_result(
        user, board, device.id, int(device.channel), DeviceStatus.ACTIVE, NOW
    )
    await store.record_command_result(
        user, board, other.id, int(other.channel), DeviceStatus.ACTIVE, NOW
    )
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


async def test_a_hash_of_another_form_is_discarded_instead_of_guessed():
    redis = aioredis.FakeRedis(decode_responses=True)
    prefix = "tests"
    store = RedisHomeStateStore(redis, prefix)
    user = UserId.parse(OWNER_UUID)
    board, _other = two_boards()
    stale = keys.state_key(prefix, user)
    await redis.hset(
        stale,
        mapping={
            "relay_states": '{"1": "ON"}',
            "temperature": "30.0",
            "board_online": "1",
        },
    )

    read_as_empty = await store.read(user)

    assert read_as_empty.relay_states == {}
    assert read_as_empty.online_boards == frozenset()
    assert not read_as_empty.reading.is_usable

    await store.record_relay_report(user, board, [True], NOW)
    rewritten = await store.read(user)

    assert await redis.hget(stale, "schema_version") == STATE_VERSION
    assert rewritten.is_relay_closed(board, 1)
    assert rewritten.board_online is False
