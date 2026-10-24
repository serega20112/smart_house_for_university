"""Почему требование автоматизации не было выполнено."""

from __future__ import annotations

from enum import StrEnum


class SkipReason(StrEnum):
    """Причина, по которой требование климата пропущено в цикле автоматизации.

    Это ситуации, в которых модель отказывается действовать по требованию, которое
    вычислитель всё-таки выдал: дом сейчас не хочет автоматику, человек вмешался
    руками, или пригодных показаний датчиков для решения нет.
    """

    AUTOMATION_DISABLED = "automation_disabled"
    MANUAL_CONTROL_ACTIVE = "manual_control_active"
    NO_SENSOR_DATA = "no_sensor_data"
    NO_SUITABLE_DEVICE = "no_suitable_device"
