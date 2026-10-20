import pytest

from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device import MAX_NAME_LENGTH, Device
from smart_home.domain.devices.device_kind import DeviceKind
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.devices.relay_channel import RelayChannel
from smart_home.domain.events import DeviceCapabilityApplied, DeviceConfigured
from smart_home.domain.exceptions import (
    InvalidDeviceNameError,
    UnsupportedCapabilityError,
)
from smart_home.domain.identifiers import DeviceId, UserId
from tests.conftest import OWNER_UUID, make_device

ALL_CAPABILITIES = frozenset(Capability)


@pytest.mark.parametrize("name", ["", "   ", "x" * (MAX_NAME_LENGTH + 1)])
def test_device_with_an_unusable_name_is_refused(name: str) -> None:
    with pytest.raises(InvalidDeviceNameError):
        Device(
            id=DeviceId.generate(),
            user_id=UserId.parse(OWNER_UUID),
            name=name,
            kind=DeviceKind.LIGHT,
            channel=RelayChannel(1),
            capabilities=ALL_CAPABILITIES,
        )


def test_device_name_is_trimmed_in_the_constructor() -> None:
    device = Device(
        id=DeviceId.generate(),
        user_id=UserId.parse(OWNER_UUID),
        name="  lamp  ",
        kind=DeviceKind.LIGHT,
        channel=RelayChannel(1),
        capabilities=ALL_CAPABILITIES,
    )

    assert device.name == "lamp"


def test_device_supports_reports_the_capability_set() -> None:
    device = make_device()

    assert device.supports(Capability.ON)
    assert not device.supports(Capability.HEAT)


def test_device_require_capability_raises_for_a_missing_capability() -> None:
    device = make_device()

    with pytest.raises(UnsupportedCapabilityError):
        device.require_capability(Capability.HEAT)


@pytest.mark.parametrize(
    ("capability", "expected"),
    [
        (Capability.ON, DeviceStatus.ACTIVE),
        (Capability.OFF, DeviceStatus.OFF),
        (Capability.COOL, DeviceStatus.COOLING),
        (Capability.HEAT, DeviceStatus.HEATING),
        (Capability.HUMIDIFY, DeviceStatus.HUMIDIFYING),
        (Capability.DEHUMIDIFY, DeviceStatus.DEHUMIDIFYING),
    ],
)
def test_device_drive_returns_the_resulting_state_and_records_the_fact(
    capability: Capability,
    expected: DeviceStatus,
) -> None:
    device = Device(
        id=DeviceId.generate(),
        user_id=UserId.parse(OWNER_UUID),
        name="unit",
        kind=DeviceKind.OUTLET,
        channel=RelayChannel(1),
        capabilities=ALL_CAPABILITIES,
    )

    state = device.drive(capability, source_is_manual=True)

    assert state is expected
    recorded = device.pull_events()
    assert len(recorded) == 1
    applied = recorded[0]
    assert isinstance(applied, DeviceCapabilityApplied)
    assert applied.capability == capability.value
    assert applied.manual is True


def test_device_drive_refuses_an_unsupported_capability() -> None:
    device = make_device()

    with pytest.raises(UnsupportedCapabilityError):
        device.drive(Capability.HEAT, source_is_manual=False)

    assert device.pull_events() == ()


def test_device_pull_events_forgets_recorded_facts() -> None:
    device = make_device()
    device.record_change()

    first = device.pull_events()
    second = device.pull_events()

    assert len(first) == 1
    assert isinstance(first[0], DeviceConfigured)
    assert second == ()


def test_device_create_assigns_an_identifier() -> None:
    device = Device.create(
        user_id=UserId.parse(OWNER_UUID),
        name="Kitchen outlet",
        kind=DeviceKind.OUTLET,
        channel=RelayChannel(3),
        capabilities=frozenset({Capability.ON, Capability.OFF}),
    )

    assert isinstance(device.id, DeviceId)


def test_device_takes_part_in_automation_only_when_enabled_and_opted_in() -> None:
    device = make_device(enabled=False, automation_enabled=False)

    assert not device.is_controllable
    assert not device.takes_part_in_automation
