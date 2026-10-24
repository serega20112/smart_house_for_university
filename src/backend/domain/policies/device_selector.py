"""Выбор устройства, для которого предназначена команда.

Здесь два вопроса: какое устройство способно выполнить способность и на какое устройство
указывает свободная ссылка. Оба — решения модели, поэтому живут в сервисе домена, а не в
наборе функций, о котором вызывающему надо помнить.

Чего этот сервис нарочно не знает, так это любого слова на любом языке. Прочитать
слово «кондиционер» как намёк на нужное устройство — дело конвейера понимания речи,
который вообще может ответить на любом языке; модель только сравнивает имена.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


class DeviceSelector:
    """Находит устройства по способности, по имени и по участию в автоматизации."""

    def first_supporting(
        self,
        devices: Iterable[Device],
        capability: Capability,
        settings: AutomationSettings | None = None,
        *,
        automation_only: bool = False,
    ) -> Device | None:
        """Возвращает первое устройство, способное выполнить способность.

        Args:
            devices: Подходящие кандидаты.
            capability: Нужная способность.
            settings: Настройка автоматизации, по которой отсеивают участников.
            automation_only: Рассматривать только участников автоматизации.

        Returns:
            Device | None: Подходящее устройство или None, когда такого нет.
        """
        for device in devices:
            if not device.is_controllable:
                continue
            if automation_only and not self._participates(device, settings):
                continue
            if device.supports(capability):
                return device
        return None

    def all_supporting(self, devices: Iterable[Device], capability: Capability) -> list[Device]:
        """Возвращает всякое устройство, способное выполнить способность.

        Args:
            devices: Подходящие кандидаты.
            capability: Нужная способность.

        Returns:
            list[Device]: Подходящие устройства в том порядке, в котором их дали.
        """
        return [
            device for device in devices if device.is_controllable and device.supports(capability)
        ]

    def by_name(self, devices: Sequence[Device], reference: str) -> Device | None:
        """Возвращает устройство, на которое ссылка указывает по имени.

        Точное имя всегда побеждает. Частично совпавшее принимается следующим — из
        него берут самое короткое, и наконец устройство, чьё собственное имя вошло в
        ссылку: именно так «включи свет на кухне» доходит до лампы, хотя во фразе
        больше, чем имя.

        Args:
            devices: Подходящие кандидаты.
            reference: Кусок имени устройства, взятый из команды человека.

        Returns:
            Device | None: Подходящее устройство или None, когда имя неизвестно.
        """
        needle = reference.strip().lower()
        if not needle:
            return None
        exact = [device for device in devices if device.name.lower() == needle]
        if exact:
            return exact[0]
        partial = [device for device in devices if needle in device.name.lower()]
        if partial:
            return min(partial, key=lambda device: len(device.name))
        contained = [device for device in devices if device.name.lower() in needle]
        if contained:
            return max(contained, key=lambda device: len(device.name))
        return None

    def of_kind(self, devices: Iterable[Device], kinds: frozenset[DeviceKind]) -> list[Device]:
        """Возвращает всякое управляемое устройство указанных назначений.

        Так языковой намёк доходит до модели: конвейер решает, какие назначения могут
        стоять за фразой, а модель решает, какие из этих устройств вообще есть.

        Args:
            devices: Подходящие кандидаты.
            kinds: Назначения, о которых могла идти речь.

        Returns:
            list[Device]: Подходящие устройства.
        """
        return [device for device in devices if device.is_controllable and device.kind in kinds]

    def owned_ids(self, devices: Iterable[Device]) -> frozenset[DeviceId]:
        """Возвращает идентификаторы всех устройств аккаунта.

        Args:
            devices: Устройства аккаунта.

        Returns:
            frozenset[DeviceId]: Идентификаторы, которые принадлежат владельцу.
        """
        return frozenset(device.id for device in devices)

    def _participates(self, device: Device, settings: AutomationSettings | None) -> bool:
        if not device.takes_part_in_automation:
            return False
        if settings is None:
            return True
        return settings.device_participates(device.id)
