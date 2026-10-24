"""Что произошло с каждым устройством, к которому применили способность."""

from __future__ import annotations

from dataclasses import dataclass

from backend.application.dto.views.device_view import DeviceView
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.devices.capability import Capability


@dataclass(frozen=True, slots=True)
class CapabilityFailure:
    """Устройство, которое плата не привела в действие.

    Отказ хранится данными, а не исключением: обход дома продолжается, даже
    когда одна плата не ответила, поэтому остальные реле всё равно получают
    команду.

    Attributes:
        device_id: Идентификатор отказавшего устройства.
        name: Имя, показанное человеку.
        reason: Машинночитаемая причина, которую сообщил транспорт.
    """

    device_id: DeviceId
    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Что произошло с устройствами, к которым применили способность.

    Attributes:
        capability: Способность, которую выполнили.
        devices: Устройства, которые удалось привести в действие.
        failed: Устройства, которые плата не приняла, с причинами отказа.
    """

    capability: Capability
    devices: tuple[DeviceView, ...] = ()
    failed: tuple[CapabilityFailure, ...] = ()
