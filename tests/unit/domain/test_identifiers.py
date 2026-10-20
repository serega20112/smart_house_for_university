from uuid import UUID

import pytest

from smart_home.domain.exceptions import MalformedIdentifierError
from smart_home.domain.identifiers import DeviceId, EspDeviceId, UserId


def test_identifiers_parse_accepted_uuid_text() -> None:
    text = "550e8400-e29b-41d4-a716-446655440000"
    parsed = UserId.parse(text)
    assert parsed.value == UUID(text)
    assert str(parsed) == text


def test_identifiers_parse_of_an_uuid_instance_keeps_the_instance() -> None:
    identity = UUID("550e8400-e29b-41d4-a716-446655440000")
    assert DeviceId.parse(identity).value == identity


def test_identifiers_generate_produces_distinct_values() -> None:
    assert EspDeviceId.generate() != EspDeviceId.generate()


def test_identifiers_generate_produces_a_valid_uuid() -> None:
    assert isinstance(EspDeviceId.generate().value, UUID)


@pytest.mark.parametrize("raw", ["", "not-a-uuid", 12345, None])
def test_identifiers_parse_refuses_broken_text(raw: object) -> None:
    with pytest.raises(MalformedIdentifierError):
        UserId.parse(raw)
