import pytest

from backend.domain.exceptions.devices import InvalidCapabilityError
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.control_source import ControlSource


@pytest.mark.parametrize("capability", list(Capability))
def test_capability_parse_with_enum_member_returns_same_member(capability: Capability) -> None:
    assert Capability.parse(capability) is capability


@pytest.mark.parametrize("capability", list(Capability))
def test_capability_parse_with_upper_case_text_returns_member(
    capability: Capability,
) -> None:
    assert Capability.parse(capability.value) is capability


@pytest.mark.parametrize("capability", list(Capability))
def test_capability_parse_with_lower_case_text_returns_member(
    capability: Capability,
) -> None:
    assert Capability.parse(capability.value.lower()) is capability


@pytest.mark.parametrize("raw", [None, "", "machinery", " capability "])
def test_capability_parse_with_unknown_value_raises(raw: object) -> None:
    with pytest.raises(InvalidCapabilityError):
        Capability.parse(raw)


@pytest.mark.parametrize("source", list(ControlSource))
def test_control_source_text_round_trip(source: ControlSource) -> None:
    assert ControlSource(source.value) is source
