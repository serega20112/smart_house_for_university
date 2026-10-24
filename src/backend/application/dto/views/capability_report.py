"""Что произошло с каждым устройством, к которому применили способность."""

from __future__ import annotations

from dataclasses import dataclass

from backend.application.dto.views.device_view import DeviceView
from backend.domain.value_objects.devices.capability import Capability


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Устройства, на которых выполнили способность.

    Attributes:
        capability: Способность, которую выполнили.
        devices: Устройства, которыми управляли.
    """

    capability: Capability
    devices: tuple[DeviceView, ...] = ()
