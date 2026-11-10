"""Проверка настроек автоматизации: значения по умолчанию, валидация допусков, события."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.domain.aggregates.automation.automation_settings import (
    DEFAULT_HUMIDITY_TOLERANCE_PERCENT,
    DEFAULT_TARGET_HUMIDITY_PERCENT,
    DEFAULT_TARGET_TEMPERATURE_C,
    DEFAULT_TEMPERATURE_TOLERANCE_C,
    AutomationSettings,
)
from backend.domain.exceptions import InvalidToleranceError
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature

OWNER_UUID = "550e8400-e29b-41d4-a716-446655440000"
CHANGED_AT = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

pytestmark = pytest.mark.unit


def make_settings() -> AutomationSettings:
    return AutomationSettings(user_id=UserId.parse(OWNER_UUID))


def test_automation_settings_defaults_are_the_documented_ones() -> None:
    """Что тестируем: значения настроек автоматизации сразу после создания.
    Что передаём: настройки, созданные только с идентификатором пользователя.
    Что ожидаем: отключённая автоматизация и документированные целевые значения и допуски."""
    # Arrange
    settings = make_settings()

    # Assert
    assert settings.enabled is False
    assert settings.target_temperature == Temperature(DEFAULT_TARGET_TEMPERATURE_C)
    assert settings.temperature_tolerance == DEFAULT_TEMPERATURE_TOLERANCE_C
    assert settings.target_humidity == Humidity(DEFAULT_TARGET_HUMIDITY_PERCENT)
    assert settings.humidity_tolerance == DEFAULT_HUMIDITY_TOLERANCE_PERCENT


def test_automation_settings_aim_at_temperature_changes_target_and_records() -> None:
    """Что тестируем: изменение целевой температуры настройками.
    Что передаём: новую целевую температуру 25.0 °C.
    Что ожидаем: цель обновлена и в домен записано ровно одно событие."""
    # Arrange
    settings = make_settings()

    # Act
    settings.aim_at_temperature(Temperature(25.0))

    # Assert
    assert settings.target_temperature == Temperature(25.0)
    assert len(settings.pull_events()) == 1


def test_automation_settings_aim_at_temperature_with_zero_tolerance_is_kept() -> None:
    """Что тестируем: валидацию нулевого допуска температуры.
    Что передаём: целевую температуру и допуск 0.0.
    Что ожидаем: нулевой допуск принят и сохранён в настройках."""
    # Arrange
    settings = make_settings()

    # Act
    settings.aim_at_temperature(Temperature(25.0), tolerance=0.0)

    # Assert
    assert settings.temperature_tolerance == 0.0


def test_automation_settings_aim_at_temperature_with_wild_tolerance_is_refused() -> None:
    """Что тестируем: отказ от недопустимого (отрицательного) допуска температуры.
    Что передаём: целевую температуру и допуск -1.0.
    Что ожидаем: исключение InvalidToleranceError, целевая температура остаётся прежней."""
    # Arrange
    settings = make_settings()

    # Act
    with pytest.raises(InvalidToleranceError):
        settings.aim_at_temperature(Temperature(25.0), tolerance=-1.0)

    # Assert
    assert settings.target_temperature == Temperature(DEFAULT_TARGET_TEMPERATURE_C)


def test_automation_settings_aim_at_humidity_with_zero_tolerance_is_kept() -> None:
    """Что тестируем: установку целевой влажности с нулевым допуском.
    Что передаём: целевую влажность 55.0 % и допуск 0.0.
    Что ожидаем: и цель, и нулевой допуск сохранены в настройках."""
    # Arrange
    settings = make_settings()

    # Act
    settings.aim_at_humidity(Humidity(55.0), tolerance=0.0)

    # Assert
    assert settings.target_humidity == Humidity(55.0)
    assert settings.humidity_tolerance == 0.0


def test_automation_settings_aim_at_humidity_with_wild_tolerance_is_refused() -> None:
    """Что тестируем: отказ от недопустимого (отрицательного) допуска влажности.
    Что передаём: целевую влажность 55.0 % и допуск -2.0.
    Что ожидаем: исключение InvalidToleranceError, целевая влажность остаётся прежней."""
    # Arrange
    settings = make_settings()

    # Act
    with pytest.raises(InvalidToleranceError):
        settings.aim_at_humidity(Humidity(55.0), tolerance=-2.0)

    # Assert
    assert settings.target_humidity == Humidity(DEFAULT_TARGET_HUMIDITY_PERCENT)


def test_automation_settings_constructed_with_a_wild_tolerance_is_refused() -> None:
    """Что тестируем: валидацию допуска при создании настроек.
    Что передаём: конструктору отрицательный допуск температуры -1.0.
    Что ожидаем: исключение InvalidToleranceError."""
    # Act
    with pytest.raises(InvalidToleranceError):
        # Arrange
        AutomationSettings(user_id=UserId.parse(OWNER_UUID), temperature_tolerance=-1.0)


def test_automation_settings_enable_records_once_and_again_only_on_a_change() -> None:
    """Что тестируем: запись события включения автоматизации.
    Что передаём: два последовательных вызова enable() на одних настройках.
    Что ожидаем: автоматизация включена, событие записано только один раз."""
    # Arrange
    settings = make_settings()

    # Act
    settings.enable()
    settings.enable()

    # Assert
    assert settings.enabled is True
    assert len(settings.pull_events()) == 1


def test_automation_settings_device_participates_without_restriction() -> None:
    """Что тестируем: участие устройств в автоматизации без списка участников.
    Что передаём: произвольное свежесгенерированное устройство.
    Что ожидаем: устройство допущено к участию."""
    # Arrange
    settings = make_settings()

    # Assert
    assert settings.device_participates(DeviceId.generate())


def test_automation_settings_device_participates_only_from_the_list() -> None:
    """Что тестируем: участие устройств в автоматизации с заданным списком участников.
    Что передаём: список из одного устройства и два устройства на проверку.
    Что ожидаем: устройство из списка допущено, устройство вне списка — нет."""


    # Arrange
    settings = make_settings()
    chosen = DeviceId.generate()
    settings.set_participants(frozenset({chosen}))

    # Act / Assert
    assert settings.device_participates(chosen)
    assert not settings.device_participates(DeviceId.generate())
