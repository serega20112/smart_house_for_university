"""Device capability selection policy."""

from __future__ import annotations

from collections.abc import Iterable

from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability, DeviceType

NAME_STEM_LENGTH = 4

TYPE_KEYWORDS: dict[DeviceType, tuple[str, ...]] = {
    DeviceType.LIGHT: ("свет", "лампа", "лампочка", "люстра", "подсветка"),
    DeviceType.AIR_CONDITIONER: ("кондиционер", "кондей", "сплит", "кондер"),
    DeviceType.HUMIDIFIER: ("увлажнитель", "увлажн", "влажность"),
    DeviceType.FAN: ("вентилятор", "проветр", "вентиляц"),
    DeviceType.HEATER: ("обогреватель", "обогрев", "батарея", "тепл"),
    DeviceType.OUTLET: ("розетк", "розетка"),
}


def find_device_for_capability(
    devices: Iterable[Device],
    capability: Capability,
    settings: AutomationSettings | None = None,
    only_automation: bool = False,
) -> Device | None:
    """Return the first enabled device that can perform the capability.

    Automation resolves devices by capability instead of by relay number, so the
    same rule works regardless of the wiring.

    Args:
        devices: Candidate devices.
        capability: Required capability.
        settings: Automation settings used to filter participants.
        only_automation: Whether only automation participants are considered.

    Returns:
        Device | None: Matching device or None when there is none.
    """
    for device in devices:
        if not device.enabled:
            continue
        if only_automation and not _participates(device, settings):
            continue
        if device.supports(capability):
            return device
    return None


def find_all_for_capability(
    devices: Iterable[Device], capability: Capability
) -> list[Device]:
    """Return every enabled device that can perform the capability.

    Args:
        devices: Candidate devices.
        capability: Required capability.

    Returns:
        list[Device]: Matching devices.
    """
    return [device for device in devices if device.enabled and device.supports(capability)]


def find_device_by_name(devices: Iterable[Device], reference: str) -> Device | None:
    """Return the device a free-form reference points at.

    An explicit name always wins. Otherwise the reference is treated as a hint
    about the device kind, so "включи свет" reaches the lamp and "включи
    кондиционер" reaches the air conditioner.

    Args:
        devices: Candidate devices.
        reference: Device name or kind taken from the user command.

    Returns:
        Device | None: Matching device or None when the reference is unknown.
    """
    needle = reference.strip().lower()
    if not needle:
        return None

    by_name = _match_by_name(devices, needle)
    if by_name is not None:
        return by_name

    return _match_by_type(devices, needle)


def _match_by_name(devices: Iterable[Device], needle: str) -> Device | None:
    exact = [device for device in devices if device.name.lower() == needle]
    if exact:
        return exact[0]
    partial = [device for device in devices if needle in device.name.lower()]
    if partial:
        return min(partial, key=lambda device: len(device.name))
    superset = [device for device in devices if device.name.lower() in needle]
    if superset:
        return max(superset, key=lambda device: len(device.name))
    return None


def _match_by_type(devices: Iterable[Device], needle: str) -> Device | None:
    candidates = [
        device
        for device in devices
        if device.enabled
        and any(_shares_stem(needle, keyword) for keyword in TYPE_KEYWORDS.get(device.type, ()))
    ]
    return candidates[0] if candidates else None


def _shares_stem(word: str, keyword: str) -> bool:
    length = min(len(word), len(keyword), NAME_STEM_LENGTH)
    return length > 0 and word[:length] == keyword[:length]


def _participates(device: Device, settings: AutomationSettings | None) -> bool:
    if not device.is_participating_in_automation:
        return False
    if settings is None:
        return True
    return settings.device_participates(device.id)
