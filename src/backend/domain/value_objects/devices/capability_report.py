"""Что произошло с каждым устройством, к которому применили способность."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_view import DeviceView


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Устройства, на которых выполнили способность.

    Attributes:
        capability: Способность, которую выполнили.
        devices: Устройства, которыми управляли.
    """

    capability: Capability
    devices: tuple[DeviceView, ...] = ()
