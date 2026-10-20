"""Shared fixtures of the unit tests."""

from __future__ import annotations

import pytest

from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_kind import DeviceKind
from smart_home.domain.devices.relay_channel import RelayChannel
from smart_home.domain.identifiers import DeviceId, UserId

OWNER_UUID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_UUID = "11111111-2222-3333-4444-555555555555"


def make_device(**overrides: object) -> Device:
    fields: dict[str, object] = {
        "id": DeviceId.generate(),
        "user_id": UserId.parse(OWNER_UUID),
        "name": "Living room light",
        "kind": DeviceKind.LIGHT,
        "channel": RelayChannel(1),
        "capabilities": frozenset({Capability.ON, Capability.OFF}),
    }
    fields.update(overrides)
    return Device(**fields)


@pytest.fixture
def owner() -> UserId:
    return UserId.parse(OWNER_UUID)


@pytest.fixture
def other_owner() -> UserId:
    return UserId.parse(OTHER_UUID)


@pytest.fixture
def light() -> Device:
    return make_device()


@pytest.fixture
def heater() -> Device:
    return Device(
        id=DeviceId.generate(),
        user_id=UserId.parse(OWNER_UUID),
        name="Hallway heater",
        kind=DeviceKind.HEATER,
        channel=RelayChannel(4),
        capabilities=frozenset({Capability.OFF, Capability.HEAT}),
    )
