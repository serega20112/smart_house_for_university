"""Объект-значение температуры.

Модель отказывается хранить температуру, которой нельзя верить, поэтому сценарию
приложения не сравнивать сырые числа с физическими границами и не сообщать значение,
которое он сам же принял мгновением раньше.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from backend.domain.exceptions import InvalidTemperatureError

MIN_CELSIUS = -40.0
MAX_CELSIUS = 80.0


@dataclass(frozen=True, slots=True, order=True)
class Temperature:
    """Температура в градусах Цельсия.

    Attributes:
        celsius: Измеренное или запрошенное значение.

    Raises:
        InvalidTemperatureError: Когда значение вне физически возможного диапазона.
    """

    celsius: float

    def __post_init__(self) -> None:
        """Проверяет физический диапазон значения.

        Raises:
            InvalidTemperatureError: Когда значение вне диапазона.
        """
        if not MIN_CELSIUS <= self.celsius <= MAX_CELSIUS:
            raise InvalidTemperatureError(self.celsius)

    def shifted_by(self, delta: float) -> Self:
        """Возвращает температуру на несколько градусов дальше от этой.

        Значение проходит ту же проверку диапазона, что и сконструированное напрямую:
        сдвиг не способ протащить за пределы физически возможного.

        Args:
            delta: Смещение в градусах Цельсия.

        Returns:
            Self: Сдвинутое значение.
        """
        return type(self)(self.celsius + delta)

    def distance_to(self, other: Temperature) -> float:
        """Возвращает расстояние от этого значения до другого.

        Args:
            other: Значение, до которого меряют расстояние.

        Returns:
            float: Разница в градусах Цельсия по модулю.
        """
        return abs(self.celsius - other.celsius)
