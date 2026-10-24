"""Одно действие внутри отложенного сценария."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability


@dataclass(frozen=True, slots=True)
class ScenarioAction:
    """Способность, о которой сценарий просит в момент начала.

    Действие называет способность и необязательную цель, а не канал реле: устройство
    выбирается, когда действие выполняется, — проводка дома может измениться, пока
    сценарий ждёт своей очереди.

    Attributes:
        capability: Способность, которую нужно выполнить.
        target_temperature: Температура, к которой действие идёт, или None, когда
            действие только что-то переключает.
    """

    capability: Capability
    target_temperature: Temperature | None = None

    @property
    def has_goal(self) -> bool:
        """Сообщает, можно ли судить, что действие достигнуто.

        Returns:
            bool: True, когда целевая температура была названа.
        """
        return self.target_temperature is not None
