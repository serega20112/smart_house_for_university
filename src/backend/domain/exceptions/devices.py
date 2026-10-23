"""Отказы устройства и его конфигурации."""

from __future__ import annotations

from backend.domain.exceptions.base import DomainError


class InvalidDeviceNameError(DomainError):
    """Имя устройства пусто или не помещается на экран.

    Attributes:
        reason: Почему значение отвергнуто.
    """

    def __init__(self, reason: str = "value is empty or too long") -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему значение отвергнуто.
        """
        super().__init__(f"Device name {reason}")
        self.reason = reason


class InvalidRelayChannelError(DomainError):
    """Номер канала реле отсутствует на железе.

    Attributes:
        channel: Отвергнутый номер канала.
        limit: Последний канал, который есть на плате.
    """

    def __init__(self, channel: int, limit: int) -> None:
        """Запоминает канал и предел платы.

        Args:
            channel: Отвергнутый номер канала.
            limit: Последний канал, который есть на плате.
        """
        super().__init__(f"relay channel {channel} is outside 1..{limit}")
        self.channel = channel
        self.limit = limit


class ChannelConflictError(DomainError):
    """Физический канал уже присоединён к другому устройству того же аккаунта.

    Attributes:
        channel: Конфликтующий канал реле.
    """

    def __init__(self, channel: int) -> None:
        """Запоминает конфликтующий канал.

        Args:
            channel: Конфликтующий канал реле.
        """
        super().__init__(f"relay channel {channel} is already wired to another device")
        self.channel = channel


class UnsupportedCapabilityError(DomainError):
    """Устройство не умеет запрошенную способность.

    Attributes:
        device_name: Имя устройства.
        capability: Запрошенная способность.
    """

    def __init__(self, device_name: str, capability: str) -> None:
        """Запоминает устройство и способность.

        Args:
            device_name: Имя устройства.
            capability: Запрошенная способность.
        """
        super().__init__(f"device {device_name!r} does not support {capability}")
        self.device_name = device_name
        self.capability = capability
