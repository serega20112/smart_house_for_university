"""Допустимый коридор климата, в котором живёт гистерезис.

Коридор хранится как цель плюс допуск, а не как два отдельных числа: только в такой
форме вызывающий не может ни переставить их местами, ни сделать отрицательными. Одна
проверка конструктора заменяет защитные abs(), которые раньше встречались в каждом
вычислении.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidMeasurementError, InvalidToleranceError


@dataclass(frozen=True, slots=True)
class ClimateBand[MeasuredT]:
    """Допустимый коридор вокруг целевого значения.

    Attributes:
        target: Значение, которое велено держать дому.
        tolerance: Насколько измерению позволено уйти, прежде чем примутся за
            устройство. Отрицательным не бывает: конструктор его отвергает, поэтому
            никому после не приходится его починять.

    Raises:
        InvalidToleranceError: Когда допуск отрицательный.
    """

    target: MeasuredT
    tolerance: float

    def __post_init__(self) -> None:
        """Проверяет допуск.

        Raises:
            InvalidToleranceError: Когда допуск отрицательный.
        """
        if self.tolerance < 0:
            raise InvalidToleranceError(self.tolerance)

    @property
    def low(self) -> float:
        """Возвращает нижнюю границу коридора."""
        return self._value_of(self.target) - self.tolerance

    @property
    def high(self) -> float:
        """Возвращает верхнюю границу коридора."""
        return self._value_of(self.target) + self.tolerance

    def contains(self, measurement: MeasuredT) -> bool:
        """Сообщает, уложилось ли измерение в коридор.

        Args:
            measurement: Значение, которое измерили датчики.

        Returns:
            bool: True, когда менять ничего не нужно.
        """
        numeric = self._value_of(measurement)
        return self.low <= numeric <= self.high

    def needs_increase(self, measurement: MeasuredT) -> bool:
        """Сообщает, оказалось ли измерение ниже коридора.

        Args:
            measurement: Значение, которое измерили датчики.

        Returns:
            bool: True, когда нужно нагрев или увлажнение.
        """
        return self._value_of(measurement) < self.low

    def needs_decrease(self, measurement: MeasuredT) -> bool:
        """Сообщает, оказалось ли измерение выше коридора.

        Args:
            measurement: Значение, которое измерили датчики.

        Returns:
            bool: True, когда нужно охлаждение или осушение.
        """
        return self._value_of(measurement) > self.high

    @staticmethod
    def _value_of(measurement: MeasuredT) -> float:
        """Приводит измерение к числу.

        Args:
            measurement: Значение, которое измерили датчики.

        Returns:
            float: Число в единицах величины.

        Raises:
            InvalidMeasurementError: Когда значение не является измерением климата.
        """
        if isinstance(measurement, bool):
            raise InvalidMeasurementError(type(measurement).__name__)
        if isinstance(measurement, (int, float)):
            return float(measurement)
        celsius = getattr(measurement, "celsius", None)
        if celsius is not None:
            return float(celsius)
        percent = getattr(measurement, "percent", None)
        if percent is not None:
            return float(percent)
        raise InvalidMeasurementError(type(measurement).__name__)
