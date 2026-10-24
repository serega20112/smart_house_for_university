"""Отказы персональной проекции дома."""

from __future__ import annotations

from backend.domain.exceptions.base import DomainError


class InvalidDashboardLayoutError(DomainError):
    """Раскладка панели нарушает инвариант агрегата.

    Attributes:
        reason: Почему раскладка отвергнута.
    """

    def __init__(self, reason: str) -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему раскладка отвергнута.
        """
        super().__init__(f"invalid dashboard layout: {reason}")
        self.reason = reason


class DashboardAccessDeniedError(DomainError):
    """Виджет ссылается на устройство, которым аккаунт не владеет.

    Attributes:
        device_id: Устройство, на которое ссылался виджет.
    """

    def __init__(self, device_id: str) -> None:
        """Запоминает чужое устройство.

        Args:
            device_id: Устройство, на которое ссылался виджет.
        """
        super().__init__(f"device {device_id} does not belong to this account")
        self.device_id = device_id


class InvalidWidgetKindError(DomainError):
    """Значение не называет вид компонента панели.

    Attributes:
        raw: Отвергнутое значение.
    """

    def __init__(self, raw: object) -> None:
        """Запоминает отвергнутое значение.

        Args:
            raw: Отвергнутое значение.
        """
        super().__init__(f"unknown widget kind: {raw!r}")
        self.raw = raw
