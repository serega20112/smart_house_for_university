import pytest

from backend.domain.exceptions import InvalidTemperatureError
from backend.domain.value_objects.climate.temperature import MAX_CELSIUS, MIN_CELSIUS, Temperature


@pytest.mark.parametrize("celsius", [MIN_CELSIUS, MAX_CELSIUS, 0.0, 21.5, -19.7])
def test_temperature_in_the_physical_range_is_valid(celsius: float) -> None:
    assert Temperature(celsius).celsius == celsius


@pytest.mark.parametrize("celsius", [MIN_CELSIUS - 1, MAX_CELSIUS + 1, -100.0, 1000.0])
def test_temperature_outside_the_physical_range_is_refused(celsius: float) -> None:
    with pytest.raises(InvalidTemperatureError):
        Temperature(celsius)


def test_temperature_shifted_by_moves_within_the_range() -> None:
    assert Temperature(20.0).shifted_by(2.5).celsius == 22.5


def test_temperature_shifted_by_out_of_range_is_refused() -> None:
    with pytest.raises(InvalidTemperatureError):
        Temperature(MAX_CELSIUS - 1).shifted_by(10)


def test_temperature_ordering_follows_the_value() -> None:
    assert Temperature(19.0) < Temperature(21.0)
