from datetime import UTC, datetime

import pytest

from smart_home.domain.climate.automation_settings import (
    DEFAULT_HUMIDITY_TOLERANCE_PERCENT,
    DEFAULT_TARGET_HUMIDITY_PERCENT,
    DEFAULT_TARGET_TEMPERATURE_C,
    DEFAULT_TEMPERATURE_TOLERANCE_C,
    AutomationSettings,
)
from smart_home.domain.climate.humidity import Humidity
from smart_home.domain.climate.temperature import Temperature
from smart_home.domain.exceptions import InvalidToleranceError
from smart_home.domain.identifiers import DeviceId, UserId

OWNER_UUID = "550e8400-e29b-41d4-a716-446655440000"
CHANGED_AT = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def make_settings() -> AutomationSettings:
    return AutomationSettings(user_id=UserId.parse(OWNER_UUID))


def test_automation_settings_defaults_are_the_documented_ones() -> None:
    settings = make_settings()

    assert settings.enabled is False
    assert settings.target_temperature == Temperature(DEFAULT_TARGET_TEMPERATURE_C)
    assert settings.temperature_tolerance == DEFAULT_TEMPERATURE_TOLERANCE_C
    assert settings.target_humidity == Humidity(DEFAULT_TARGET_HUMIDITY_PERCENT)
    assert settings.humidity_tolerance == DEFAULT_HUMIDITY_TOLERANCE_PERCENT


def test_automation_settings_aim_at_temperature_changes_target_and_records() -> None:
    settings = make_settings()

    settings.aim_at_temperature(Temperature(25.0))

    assert settings.target_temperature == Temperature(25.0)
    assert len(settings.pull_events()) == 1


def test_automation_settings_aim_at_temperature_with_zero_tolerance_is_kept() -> None:
    settings = make_settings()

    settings.aim_at_temperature(Temperature(25.0), tolerance=0.0)

    assert settings.temperature_tolerance == 0.0


def test_automation_settings_aim_at_temperature_with_wild_tolerance_is_refused() -> None:
    settings = make_settings()

    with pytest.raises(InvalidToleranceError):
        settings.aim_at_temperature(Temperature(25.0), tolerance=-1.0)

    assert settings.target_temperature == Temperature(DEFAULT_TARGET_TEMPERATURE_C)


def test_automation_settings_aim_at_humidity_with_zero_tolerance_is_kept() -> None:
    settings = make_settings()

    settings.aim_at_humidity(Humidity(55.0), tolerance=0.0)

    assert settings.target_humidity == Humidity(55.0)
    assert settings.humidity_tolerance == 0.0


def test_automation_settings_aim_at_humidity_with_wild_tolerance_is_refused() -> None:
    settings = make_settings()

    with pytest.raises(InvalidToleranceError):
        settings.aim_at_humidity(Humidity(55.0), tolerance=-2.0)

    assert settings.target_humidity == Humidity(DEFAULT_TARGET_HUMIDITY_PERCENT)


def test_automation_settings_constructed_with_a_wild_tolerance_is_refused() -> None:
    with pytest.raises(InvalidToleranceError):
        AutomationSettings(user_id=UserId.parse(OWNER_UUID), temperature_tolerance=-1.0)


def test_automation_settings_enable_records_once_and_again_only_on_a_change() -> None:
    settings = make_settings()

    settings.enable()
    settings.enable()

    assert settings.enabled is True
    assert len(settings.pull_events()) == 1


def test_automation_settings_device_participates_without_restriction() -> None:
    settings = make_settings()

    assert settings.device_participates(DeviceId.generate())


def test_automation_settings_device_participates_only_from_the_list() -> None:
    settings = make_settings()
    chosen = DeviceId.generate()
    settings.set_participants(frozenset({chosen}))

    assert settings.device_participates(chosen)
    assert not settings.device_participates(DeviceId.generate())
