"""Логическое устройство умного дома.

Физическое реле -- это не устройство. Соответствие «устройство -- канал» хранится
здесь, поэтому человек сам решает, что значит канал, не трогая прошивку; именно
поэтому любое правило автоматизации говорит о способностях, а не о номерах реле.

Сущность владеет своими правилами: она знает, какую способность может выполнить,
когда участвует в автоматизации и как менять свою настройку. Полям сущности извне
не присваивают.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from backend.domain.events import DeviceCapabilityApplied, DeviceConfigured
from backend.domain.exceptions import InvalidDeviceNameError, UnsupportedCapabilityError
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_channel import RelayChannel

MAX_NAME_LENGTH = 120


@dataclass
class Device:
    """Устройство, которое человек настроил на канале реле своей платы.

    Attributes:
        id: Идентификатор, выданный при создании.
        user_id: Владелец устройства.
        name: Имя, показанное человеку.
        kind: Для чего устройство.
        channel: Канал реле, к которому устройство подключено.
        capabilities: Действия, которые устройство умеет.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.

    Raises:
        InvalidDeviceNameError: Когда имя пустое или слишком длинное.
    """

    id: DeviceId
    user_id: UserId
    name: str
    kind: DeviceKind
    channel: RelayChannel
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    enabled: bool = True
    automation_enabled: bool = True
    version: int = 0
    _events: list[DeviceConfigured | DeviceCapabilityApplied] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Проверяет имя устройства.

        Raises:
            InvalidDeviceNameError: Когда имя пустое или слишком длинное.
        """
        trimmed = self.name.strip()
        if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
            raise InvalidDeviceNameError()
        self.name = trimmed

    def supports(self, capability: Capability) -> bool:
        """Сообщает, умеет ли устройство выполнять способность.

        Args:
            capability: Проверяемая способность.

        Returns:
            bool: True, когда устройство на это способно.
        """
        return capability in self.capabilities

    def require_capability(self, capability: Capability) -> None:
        """Отказывает в способности, которую устройство не может выполнить.

        Args:
            capability: Требованная способность.

        Raises:
            UnsupportedCapabilityError: Когда способность не поддерживается.
        """
        if not self.supports(capability):
            raise UnsupportedCapabilityError(self.name, capability.value)

    @property
    def is_controllable(self) -> bool:
        """Сообщает, можно ли этим устройством хоть как-то управлять."""
        return self.enabled

    @property
    def takes_part_in_automation(self) -> bool:
        """Сообщает, разрешено ли вести это устройство автоматизации."""
        return self.enabled and self.automation_enabled

    def drive(self, capability: Capability, source_is_manual: bool) -> DeviceStatus:
        """Записывает, что на этом устройстве выполнили способность.

        Сущность не разговаривает с железом: она проверяет запрос, хранит факт и
        говорит, каким устройство окажется после.

        Args:
            capability: Выполненная способность.
            source_is_manual: Просил ли человек или это автоматика/сценарий.

        Returns:
            DeviceStatus: Состояние, которого устройство достигло.

        Raises:
            UnsupportedCapabilityError: Когда способность не поддерживается.
        """
        self.require_capability(capability)
        result = DeviceStatus.after(capability)
        self._events.append(
            DeviceCapabilityApplied(
                user_id=self.user_id,
                device_id=self.id,
                device_name=self.name,
                channel=int(self.channel),
                capability=capability.value,
                manual=source_is_manual,
            )
        )
        return result

    def record_change(self) -> None:
        """Записывает, что настройка этого устройства изменилась."""
        self._events.append(DeviceConfigured(user_id=self.user_id, device_id=self.id))

    def pull_events(self) -> tuple[DeviceConfigured | DeviceCapabilityApplied, ...]:
        """Возвращает записанные факты и забывает их.

        Returns:
            tuple[DeviceConfigured | DeviceCapabilityApplied, ...]: Факты с
            прошлого обращения.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def reconfigure(
        self,
        *,
        name: str | None = None,
        kind: DeviceKind | None = None,
        channel: RelayChannel | None = None,
        capabilities: frozenset[Capability] | None = None,
        enabled: bool | None = None,
        automation_enabled: bool | None = None,
    ) -> None:
        """Применяет частичное изменение настройки.

        Args:
            name: Новое имя или None оставить нынешнее.
            kind: Новое назначение или None оставить нынешнее.
            channel: Новый канал реле или None оставить нынешний.
            capabilities: Новые способности или None оставить нынешние.
            enabled: Новый признак доступности или None оставить нынешний.
            automation_enabled: Новый признак автоматизации или None оставить
                нынешний.

        Raises:
            InvalidDeviceNameError: Когда новое имя пустое или слишком длинное.
        """
        if name is not None:
            trimmed = name.strip()
            if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
                raise InvalidDeviceNameError()
            self.name = trimmed
        if kind is not None:
            self.kind = kind
        if channel is not None:
            self.channel = channel
        if capabilities is not None:
            self.capabilities = frozenset(capabilities)
        if enabled is not None:
            self.enabled = enabled
        if automation_enabled is not None:
            self.automation_enabled = automation_enabled

    @classmethod
    def create(
        cls,
        user_id: UserId,
        name: str,
        kind: DeviceKind,
        channel: RelayChannel,
        capabilities: frozenset[Capability],
        *,
        enabled: bool = True,
        automation_enabled: bool = True,
    ) -> Self:
        """Строит новое устройство с собственным идентификатором.

        Args:
            user_id: Владелец устройства.
            name: Имя, показанное человеку.
            kind: Для чего устройство.
            channel: Канал реле, к которому устройство подключают.
            capabilities: Действия, которые устройство умеет.
            enabled: Разрешено ли устройством управлять вообще.
            automation_enabled: Участвует ли устройство в автоматизации.

        Returns:
            Self: Созданное устройство.
        """
        return cls(
            id=DeviceId.generate(),
            user_id=user_id,
            name=name,
            kind=kind,
            channel=channel,
            capabilities=capabilities,
            enabled=enabled,
            automation_enabled=automation_enabled,
        )
