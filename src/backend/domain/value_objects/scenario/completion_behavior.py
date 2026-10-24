"""Что случится с устройствами, когда сценарий закончится."""

from __future__ import annotations

from enum import StrEnum

from backend.domain.exceptions.scenarios import InvalidCompletionBehaviorError
from backend.domain.value_objects.devices.device_status import DeviceStatus


class CompletionBehavior(StrEnum):
    """Как закончившийся сценарий оставляет дом."""

    LEAVE_TO_AUTOMATION = "LEAVE_TO_AUTOMATION"
    SWITCH_EVERYTHING_OFF = "SWITCH_EVERYTHING_OFF"
    RESTORE_CAPTURED_STATE = "RESTORE_CAPTURED_STATE"

    def status_to_apply(self, captured_status: DeviceStatus | None) -> DeviceStatus | None:
        """Возвращает состояние, в которое устройство нужно вернуть.

        Args:
            captured_status: Состояние устройства до начала сценария, или None,
                когда для него ничего не снимали.

        Returns:
            DeviceStatus | None: Состояние возврата, или None, когда устройство
            оставят в покое.
        """
        if self is CompletionBehavior.LEAVE_TO_AUTOMATION:
            return None
        if self is CompletionBehavior.SWITCH_EVERYTHING_OFF:
            return DeviceStatus.OFF
        return captured_status

    @classmethod
    def parse(cls, raw: object) -> CompletionBehavior:
        """Читает поведение из значения, пришедшего извне.

        Args:
            raw: Имя поведения или его член перечисления.

        Returns:
            CompletionBehavior: Прочитанное поведение.

        Raises:
            InvalidCompletionBehaviorError: Когда значение не называет поведение.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise InvalidCompletionBehaviorError(raw)
        try:
            return cls(str(raw).strip().upper())
        except ValueError as error:
            raise InvalidCompletionBehaviorError(raw) from error
