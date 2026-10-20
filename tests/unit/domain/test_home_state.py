from datetime import UTC, datetime

from smart_home.domain.climate.climate_reading import ClimateReading
from smart_home.domain.climate.home_state import HomeState
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.devices.relay_state import RelayState
from smart_home.domain.identifiers import UserId
from tests.conftest import OWNER_UUID, make_device

REPORTED_AT = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
TEN_MINUTES_LATER = datetime(2026, 5, 1, 12, 10, tzinfo=UTC)
AFTER_WINDOW = datetime(2026, 5, 1, 12, 31, tzinfo=UTC)
UNCAPPED_OVERRIDE = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)


def make_state() -> HomeState:
    return HomeState(user_id=UserId.parse(OWNER_UUID), board_online=True)


def test_home_state_apply_relay_report_records_the_positions() -> None:
    state = make_state()

    changed = state.apply_relay_report([True, False, True], REPORTED_AT)

    assert changed == (1, 3)
    assert state.relay_states[1] is RelayState.ON
    assert state.relay_states[3] is RelayState.ON
    assert state.changed_at == REPORTED_AT


def test_home_state_apply_relay_report_reports_only_the_change() -> None:
    state = make_state()
    state.apply_relay_report([True, False], REPORTED_AT)

    changed = state.apply_relay_report([True, True], REPORTED_AT)

    assert changed == (2,)


def test_home_state_without_a_board_is_unavailable() -> None:
    state = make_state()
    state.set_board_available(False, REPORTED_AT)
    device = make_device()

    assert state.status_of(device) is DeviceStatus.UNAVAILABLE


def test_home_state_status_for_an_open_relay_is_off() -> None:
    state = make_state()
    device = make_device()

    assert state.status_for(device.id, int(device.channel)) is DeviceStatus.OFF


def test_home_state_apply_command_records_the_mode() -> None:
    state = make_state()
    device = make_device()
    state.apply_relay_report([True], REPORTED_AT)

    state.apply_command(device, DeviceStatus.ACTIVE, REPORTED_AT)

    assert state.status_of(device) is DeviceStatus.ACTIVE
    assert state.is_relay_closed(1)


def test_home_state_apply_reading_keeps_the_values_the_sensor_did_not_measure() -> None:
    state = make_state()
    state.apply_reading(ClimateReading.measured(21.5, 40.0), REPORTED_AT)

    latest = state.apply_reading(ClimateReading.measured(None, 45.0), REPORTED_AT)

    assert state.reading.temperature is not None
    assert state.reading.temperature.celsius == 21.5
    assert state.reading.humidity is not None
    assert state.reading.humidity.percent == 45.0
    assert latest.temperature is None
    assert latest.humidity is not None


def test_home_state_apply_reading_with_a_zero_degree_report_is_kept() -> None:
    state = make_state()

    state.apply_reading(ClimateReading.measured(0.0, None), REPORTED_AT)

    assert state.reading.temperature is not None
    assert state.reading.temperature.celsius == 0.0


def test_home_state_forget_device_drops_its_mode() -> None:
    state = make_state()
    device = make_device()
    state.apply_command(device, DeviceStatus.ACTIVE, REPORTED_AT)

    state.forget_device(device.id)

    assert state.device_modes.get(device.id) is None


def test_home_state_manual_override_suspends_automation_inside_the_window() -> None:
    state = make_state()

    state.suspend_automation_for(REPORTED_AT, 30)

    assert state.is_automation_suspended(TEN_MINUTES_LATER)
    assert not state.is_automation_suspended(AFTER_WINDOW)


def test_home_state_resume_automation_ends_the_window() -> None:
    state = make_state()
    state.suspend_automation_until(UNCAPPED_OVERRIDE)

    state.resume_automation()

    assert not state.is_automation_suspended(REPORTED_AT)
