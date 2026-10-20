import pytest

from smart_home.domain.climate.humidity import MAX_PERCENT, MIN_PERCENT, Humidity
from smart_home.domain.exceptions import InvalidHumidityError


@pytest.mark.parametrize("percent", [MIN_PERCENT, MAX_PERCENT, 45.0, 63.5])
def test_humidity_in_the_range_is_valid(percent: float) -> None:
    assert Humidity(percent).percent == percent


@pytest.mark.parametrize("percent", [MIN_PERCENT - 1, MAX_PERCENT + 1, -5.0, 1000.0])
def test_humidity_outside_the_range_is_refused(percent: float) -> None:
    with pytest.raises(InvalidHumidityError):
        Humidity(percent)


def test_humidity_shifted_by_moves_within_the_range() -> None:
    assert Humidity(40.0).shifted_by(3.0).percent == 43.0


def test_humidity_shifted_by_clamps_at_the_boundary() -> None:
    assert Humidity(MAX_PERCENT - 1).shifted_by(10).percent == MAX_PERCENT


def test_humidity_distance_to_measures_the_gap() -> None:
    assert Humidity(40.0).distance_to(Humidity(43.5)) == 3.5
