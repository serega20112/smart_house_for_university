import pytest

from backend.domain.exceptions.devices import InvalidDeviceKindError
from backend.domain.value_objects.devices.device_kind import DeviceKind


@pytest.mark.parametrize("kind", list(DeviceKind))
def test_device_kind_parse_with_enum_member_returns_same_member(
    kind: DeviceKind,
) -> None:
    assert DeviceKind.parse(kind) is kind


@pytest.mark.parametrize("kind", list(DeviceKind))
def test_device_kind_parse_with_upper_case_text_returns_member(
    kind: DeviceKind,
) -> None:
    assert DeviceKind.parse(kind.value) is kind


@pytest.mark.parametrize("raw", [None, "", "vacuum"])
def test_device_kind_parse_with_unknown_value_raises(raw: object) -> None:
    with pytest.raises(InvalidDeviceKindError):
        DeviceKind.parse(raw)
