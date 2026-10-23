"""Всё, что нужно одному экрану интерфейса."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.automation.automation_view import AutomationView
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.domain.value_objects.home.reading_view import ReadingView
from backend.domain.value_objects.scenario.scenario_view import ScenarioView


@dataclass(frozen=True, slots=True)
class HomeSnapshotView:
    """Состояние всего дома сразу для одного экрана.

    Изменчивую часть читают один раз, хранимую — один раз, поэтому числа на
    экране достаточно близки по времени, чтобы им можно было верить, а не
    приходить из двух источников с разницей в момент.

    Attributes:
        reading: Значения климата прямо сейчас.
        board_online: Подключена ли хоть одна плата аккаунта.
        automation_suspended: Сдерживает ли ручное управление автоматизацию.
        devices: Устройства вместе с их текущим состоянием.
        automation: Настройки автоматизации.
        active_scenarios: Сценарии, которые пока важнее автоматизации.
    """

    reading: ReadingView
    board_online: bool
    automation_suspended: bool
    devices: tuple[DeviceView, ...]
    automation: AutomationView
    active_scenarios: tuple[ScenarioView, ...]
