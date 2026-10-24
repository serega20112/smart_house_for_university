"""Логическое устройство умного дома.

Физическое реле устройством не является. Соответствие «устройство — канал»
хранится здесь, поэтому человек решает, что означает канал, не трогая прошивку;
поэтому же любое правило автоматизации говорит о способностях, а не о номерах
реле.

Сущность владеет своими правилами: она знает, какую способность умеет выполнить,
когда участвует в автоматизации и как менять настройки. Поля сущности не
присваиваются снаружи.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from backend.domain.events import DeviceCapabilityApplied, DeviceConfigured
from backend.domain.exceptions import UnsupportedCapabilityError
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_name import DeviceName
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_channel import RelayChannel


@dataclass
class Device:
    """Логическое устройство умного дома.

    Attributes:
        id: Идентификатор, выданный при создании.
        user_id: Владелец устройства.
        name: Имя, показанное человеку.
        kind: Для чего устройство.
        channel: Канал реле, к которому подключено устройство.
        board_id: Плата, на которой стоит канал, или None, когда плата ещё не
            сопряжена (дом с одной платой, которую разрешает реестр присутствия).
        capabilities: Действия, которые устройство умеет выполнять.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
        version: Счётчик ревизий строки.
        _events: Внутренний журнал фактов.

    Raises:
        InvalidDeviceNameError: Когда имя пусто или слишком длинно.
    """

    id: DeviceId
    user_id: UserId
    name: str
    kind: DeviceKind
    channel: RelayChannel
    board_id: EspDeviceId | None = None
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
            InvalidDeviceNameError: Когда имя пусто или слишком длинно.
        """
        self.name = DeviceName.parse(self.name).value

    def supports(self, capability: Capability) -> bool:
        """Сообщает, умеет ли устройство выполнить способность.

        Args:
            capability: Проверяемая способность.

        Returns:
            bool: True, когда устройство умеет эту способность.
        """
        return capability in self.capabilities

    def require_capability(self, capability: Capability) -> None:
        """Отвергает способность, которую устройство выполнить не может.

        Args:
            capability: Запрошенная способность.

        Raises:
            UnsupportedCapabilityError: Когда способность не поддерживается.
        """
        if not self.supports(capability):
            raise UnsupportedCapabilityError(self.name, capability.value)

    @property
    def is_controllable(self) -> bool:
        """Сообщает, можно ли управлять устройством вообще."""
        return self.enabled

    @property
    def takes_part_in_automation(self) -> bool:
        """Сообщает, разрешено ли устройство в автоматизации."""
        return self.enabled and self.automation_enabled

    def drive(self, capability: Capability, source_is_manual: bool) -> DeviceStatus:
        """Записывает, что над устройством выполнили способность.

        Сущность не разговаривает с железом: она проверяет запрос, запоминает факт и
        сообщает, каким устройство станет после него.

        Args:
            capability: Выполненная способность.
            source_is_manual: Попросил ли человек или автоматика со сценарием.

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
        """Записывает, что настройка устройства изменилась."""
        self._events.append(DeviceConfigured(user_id=self.user_id, device_id=self.id))

    def pull_events(self) -> tuple[DeviceConfigured | DeviceCapabilityApplied, ...]:
        """Возвращает записанные факты и забывает их.

        Returns:
            tuple[DeviceConfigured | DeviceCapabilityApplied, ...]: Факты,
            записанные с прошлого обращения.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def detach_from_board(self) -> None:
        """Оставляет устройство в доме, но без платы.

        Отвязка платы не стирает устройство: имя, способности и участие в
        автоматизации остаются, пока человек не решит иначе. Канал при этом
        перестаёт быть адресом реле, поэтому управлять устройством можно будет
        только после того, как ему назначат другую плату.
        """
        self.board_id = None

    def reconfigure(
        self,
        *,
        name: str | None = None,
        kind: DeviceKind | None = None,
        channel: RelayChannel | None = None,
        board_id: EspDeviceId | None = None,
        capabilities: frozenset[Capability] | None = None,
        enabled: bool | None = None,
        automation_enabled: bool | None = None,
    ) -> None:
        """Применяет частичное изменение настройки.

        Перенос устройства на другую плату — такая же штатная правка, как смена
        канала: канал существует внутри платы, поэтому плата и канал меняются вместе.

        Args:
            name: Новое имя или None, чтобы оставить текущее.
            kind: Новый тип или None, чтобы оставить текущий.
            channel: Новый канал реле или None, чтобы оставить текущий.
            board_id: Новая плата или None, чтобы оставить текущую.
            capabilities: Новые способности или None, чтобы оставить текущие.
            enabled: Новый признак управления или None, чтобы оставить текущий.
            automation_enabled: Новый признак участия в автоматизации или None.

        Raises:
            InvalidDeviceNameError: Когда новое имя пусто или слишком длинно.
        """
        if name is not None:
            self.name = DeviceName.parse(name).value
        if kind is not None:
            self.kind = kind
        if channel is not None:
            self.channel = channel
        if board_id is not None:
            self.board_id = board_id
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
        board_id: EspDeviceId | None = None,
        enabled: bool = True,
        automation_enabled: bool = True,
    ) -> Self:
        """Создаёт новое устройство со сгенерированным идентификатором.

        Args:
            user_id: Владелец устройства.
            name: Имя, показанное человеку.
            kind: Для чего устройство.
            channel: Канал реле, к которому подключено устройство.
            capabilities: Действия, которые устройство умеет выполнять.
            board_id: Плата, на которой стоит канал, или None для дома с одной платой.
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
            board_id=board_id,
            capabilities=capabilities,
            enabled=enabled,
            automation_enabled=automation_enabled,
        )
