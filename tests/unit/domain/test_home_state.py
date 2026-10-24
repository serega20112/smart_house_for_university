"""The home state keeps every board apart from its neighbours.

Channels of two boards share numbers but not contacts, sensors of two boards
measure different rooms, and availability belongs to a board, not to the account.
The rules under test are the ones a home of two boards needs to make correct
decisions instead of announcing somebody else's device.
"""

from datetime import UTC, datetime

from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState
from tests.conftest import OWNER_UUID, make_device

REPORTED_AT = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
TEN_MINUTES_LATER = datetime(2026, 5, 1, 12, 10, tzinfo=UTC)
AFTER_WINDOW = datetime(2026, 5, 1, 12, 31, tzinfo=UTC)
UNCAPPED_OVERRIDE = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)

LIVING_ROOM = EspDeviceId.generate()
GARAGE = EspDeviceId.generate()


def make_state(*online: EspDeviceId) -> HomeState:
    """Build a home with the given boards answering.

    Args:
        online: Boards that answer right now.

    Returns:
        HomeState: Empty home of the shared owner.
    """
    return HomeState(user_id=UserId.parse(OWNER_UUID), online_boards=frozenset(online))


def test_home_state_apply_relay_report_records_the_positions() -> None:
    state = make_state(LIVING_ROOM)

    changed = state.apply_relay_report(LIVING_ROOM, [True, False, True], REPORTED_AT)

    assert changed == (1, 3)
    assert state.is_relay_closed(LIVING_ROOM, 1)
    assert state.is_relay_closed(LIVING_ROOM, 3)
    assert state.changed_at == REPORTED_AT


def test_home_state_apply_relay_report_reports_only_the_change() -> None:
    state = make_state(LIVING_ROOM)
    state.apply_relay_report(LIVING_ROOM, [True, False], REPORTED_AT)

    changed = state.apply_relay_report(LIVING_ROOM, [True, True], REPORTED_AT)

    assert changed == (2,)


def test_two_boards_do_not_share_a_channel() -> None:
    state = make_state(LIVING_ROOM, GARAGE)

    state.apply_relay_report(LIVING_ROOM, [True], REPORTED_AT)
    moved = state.apply_relay_report(GARAGE, [False], REPORTED_AT)

    assert moved == ()
    assert state.relay_states[LIVING_ROOM] == {1: RelayState.ON}
    assert state.relay_states[GARAGE] == {1: RelayState.OFF}


def test_home_state_without_an_answering_board_is_unavailable() -> None:
    state = make_state()
    device = make_device(board_id=LIVING_ROOM)

    assert state.status_of(device) is DeviceStatus.UNAVAILABLE


def test_home_state_of_a_device_left_without_a_board_follows_the_only_one() -> None:
    state = make_state(LIVING_ROOM)
    device = make_device()

    assert state.status_of(device) is DeviceStatus.OFF

    state.apply_relay_report(LIVING_ROOM, [True], REPORTED_AT)

    assert state.status_of(device) is DeviceStatus.ACTIVE


def test_home_state_of_a_device_left_without_a_board_is_unavailable_among_many() -> None:
    state = make_state(LIVING_ROOM, GARAGE)
    device = make_device()

    assert state.status_of(device) is DeviceStatus.UNAVAILABLE


def test_home_state_status_for_an_open_relay_is_off() -> None:
    state = make_state(LIVING_ROOM)
    device = make_device(board_id=LIVING_ROOM)

    assert state.status_of(device) is DeviceStatus.OFF


def test_home_state_apply_command_records_the_mode_of_that_board() -> None:
    state = make_state(LIVING_ROOM, GARAGE)
    device = make_device(board_id=LIVING_ROOM)
    state.apply_relay_report(LIVING_ROOM, [True], REPORTED_AT)

    state.apply_command(
        LIVING_ROOM, device.id, int(device.channel), DeviceStatus.ACTIVE, REPORTED_AT
    )

    assert state.status_of(device) is DeviceStatus.ACTIVE
    assert state.is_relay_closed(LIVING_ROOM, 1)


def test_home_state_apply_reading_keeps_the_values_the_sensor_did_not_measure() -> None:
    state = make_state(LIVING_ROOM)
    state.apply_reading(LIVING_ROOM, ClimateReading.measured(21.5, 40.0), REPORTED_AT)

    latest = state.apply_reading(LIVING_ROOM, ClimateReading.measured(None, 45.0), REPORTED_AT)

    assert state.reading.temperature is not None
    assert state.reading.temperature.celsius == 21.5
    assert state.reading.humidity is not None
    assert state.reading.humidity.percent == 45.0
    assert latest.temperature is None
    assert latest.humidity is not None


def test_home_state_apply_reading_of_a_second_board_keeps_the_first() -> None:
    state = make_state(LIVING_ROOM, GARAGE)
    state.apply_reading(LIVING_ROOM, ClimateReading.measured(21.5, 40.0), REPORTED_AT)

    state.apply_reading(GARAGE, ClimateReading.measured(9.0, None), REPORTED_AT)

    living_temperature = state.readings[LIVING_ROOM].temperature
    garage_temperature = state.readings[GARAGE].temperature
    assert living_temperature is not None and living_temperature.celsius == 21.5
    assert garage_temperature is not None and garage_temperature.celsius == 9.0
    assert state.reading.temperature is not None and state.reading.temperature.celsius == 9.0


def test_home_state_apply_reading_with_a_zero_degree_report_is_kept() -> None:
    state = make_state(LIVING_ROOM)

    state.apply_reading(LIVING_ROOM, ClimateReading.measured(0.0, None), REPORTED_AT)

    assert state.reading.temperature is not None
    assert state.reading.temperature.celsius == 0.0


def test_home_state_losing_a_board_keeps_the_other_one_online() -> None:
    state = make_state(LIVING_ROOM, GARAGE)

    went_away = state.set_board_available(LIVING_ROOM, False, REPORTED_AT)

    assert went_away is True
    assert state.online_boards == frozenset({GARAGE})
    assert state.board_online is True


def test_home_state_forget_device_drops_its_mode() -> None:
    state = make_state(LIVING_ROOM)
    device = make_device(board_id=LIVING_ROOM)
    state.apply_command(
        LIVING_ROOM, device.id, int(device.channel), DeviceStatus.ACTIVE, REPORTED_AT
    )

    state.forget_device(device.id)

    assert state.device_modes.get(device.id) is None


def test_home_state_manual_override_suspends_automation_inside_the_window() -> None:
    state = make_state(LIVING_ROOM)

    state.suspend_automation_for(REPORTED_AT, 30)

    assert state.is_automation_suspended(TEN_MINUTES_LATER)
    assert not state.is_automation_suspended(AFTER_WINDOW)


def test_home_state_resume_automation_ends_the_window() -> None:
    state = make_state(LIVING_ROOM)
    state.suspend_automation_until(UNCAPPED_OVERRIDE)

    state.resume_automation()

    assert not state.is_automation_suspended(REPORTED_AT)
