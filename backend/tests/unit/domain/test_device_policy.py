"""Tests of the device selection policy."""

from __future__ import annotations

from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability, DeviceType
from smart_home_backend.domain.policies import (
    find_all_for_capability,
    find_device_by_name,
    find_device_for_capability,
)


def cooler(id_: int, name: str, channel: int, **kwargs) -> Device:
    return Device(
        id=id_,
        name=name,
        type=DeviceType.AIR_CONDITIONER,
        physical_channel=channel,
        capabilities=frozenset({Capability.OFF, Capability.COOL, Capability.HEAT}),
        **kwargs,
    )


def test_capability_selects_device_instead_of_channel() -> None:
    devices = [cooler(1, "Кондиционер", 4)]
    assert find_device_for_capability(devices, Capability.COOL) is devices[0]


def test_disabled_device_is_skipped() -> None:
    devices = [cooler(1, "Кондиционер", 4, enabled=False)]
    assert find_device_for_capability(devices, Capability.COOL) is None


def test_device_outside_automation_is_skipped(air_conditioner: Device) -> None:
    excluded = Device(
        id=air_conditioner.id,
        name=air_conditioner.name,
        type=air_conditioner.type,
        physical_channel=air_conditioner.physical_channel,
        capabilities=air_conditioner.capabilities,
        automation_enabled=False,
    )
    assert find_device_for_capability([excluded], Capability.COOL, only_automation=True) is None


def test_settings_restrict_participants(air_conditioner: Device) -> None:
    settings = AutomationSettings(participating_device_ids=frozenset({99}))
    assert (
        find_device_for_capability(
            [air_conditioner], Capability.COOL, settings=settings, only_automation=True
        )
        is None
    )


def test_find_all_returns_every_match(air_conditioner: Device, light: Device) -> None:
    assert find_all_for_capability([air_conditioner, light], Capability.OFF) == [
        air_conditioner,
        light,
    ]


def test_device_is_matched_by_exact_name(air_conditioner: Device) -> None:
    assert find_device_by_name([air_conditioner], "кондиционер") is air_conditioner


def test_device_is_matched_by_name_fragment(air_conditioner: Device) -> None:
    assert find_device_by_name([air_conditioner], "кондиц") is air_conditioner


def test_unknown_reference_returns_nothing(air_conditioner: Device) -> None:
    assert find_device_by_name([air_conditioner], "чайник") is None


def test_empty_reference_returns_nothing(air_conditioner: Device) -> None:
    assert find_device_by_name([air_conditioner], "  ") is None
