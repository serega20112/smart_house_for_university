import pytest

from backend.domain.exceptions import InvalidToleranceError
from backend.domain.value_objects.climate.tolerance import MAX_TOLERANCE, Tolerance


@pytest.mark.parametrize("value", [0.0, MAX_TOLERANCE, 1.0, 4.5])
def test_tolerance_within_the_limits_is_valid(value: float) -> None:
    assert Tolerance(value).value == value


@pytest.mark.parametrize("value", [-0.1, MAX_TOLERANCE + 1, -25.0])
def test_tolerance_outside_the_limits_is_refused(value: float) -> None:
    with pytest.raises(InvalidToleranceError):
        Tolerance(value)


def test_tolerance_converts_to_float() -> None:
    assert float(Tolerance(2.5)) == 2.5
