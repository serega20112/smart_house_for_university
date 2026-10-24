"""Объект-значение относительной влажности."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from backend.domain.exceptions import InvalidHumidityError

MIN_PERCENT = 0.0
MAX_PERCENT = 100.0


@dataclass(frozen=True, slots=True, order=True)
class Humidity:
    """Относительная влажность в процентах.

    Attributes:
        percent: Измеренное или запрошенное значение.

    Raises:
        InvalidHumidityError: Когда значение вне допустимого диапазона.
    """

    percent: float

    def __post_init__(self) -> None:
        """Проверяет диапазон значения.

        Raises:
            InvalidHumidityError: Когда значение вне диапазона.
        """
        if not MIN_PERCENT <= self.percent <= MAX_PERCENT:
            raise InvalidHumidityError(self.percent)

    def shifted_by(self, delta: float) -> Self:
        """Возвращает влажность на несколько процентов дальше, не выходя за границы.

        Args:
            delta: Смещение в процентах.

        Returns:
            Self: Сдвинутое значение.
        """
        clamped = min(MAX_PERCENT, max(MIN_PERCENT, self.percent + delta))
        return type(self)(clamped)

    def distance_to(self, other: Humidity) -> float:
        """Возвращает расстояние от этого значения до другого.

        Args:
            other: Значение, до которого меряют расстояние.

        Returns:
            float: Разница в процентах по модулю.
        """
        return abs(self.percent - other.percent)
