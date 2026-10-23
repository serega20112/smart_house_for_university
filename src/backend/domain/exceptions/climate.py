"""Отказы значений климата."""

from __future__ import annotations

from backend.domain.exceptions.base import DomainError


class InvalidTemperatureError(DomainError):
    """Температура вне физически возможного диапазона.

    Attributes:
        celsius: Отвергнутое значение.
    """

    def __init__(self, celsius: float) -> None:
        """Запоминает отвергнутое значение.

        Args:
            celsius: Отвергнутое значение.
        """
        super().__init__(f"temperature out of range: {celsius}")
        self.celsius = celsius


class InvalidHumidityError(DomainError):
    """Относительная влажность вне диапазона ноль — сто процентов.

    Attributes:
        percent: Отвергнутое значение.
    """

    def __init__(self, percent: float) -> None:
        """Запоминает отвергнутое значение.

        Args:
            percent: Отвергнутое значение.
        """
        super().__init__(f"humidity out of range: {percent}")
        self.percent = percent


class InvalidToleranceError(DomainError):
    """Отрицательный допуск не является полосой расхождения.

    Attributes:
        tolerance: Отвергнутое значение.
    """

    def __init__(self, tolerance: float) -> None:
        """Запоминает отвергнутое значение.

        Args:
            tolerance: Отвергнутое значение.
        """
        super().__init__(f"tolerance must not be negative: {tolerance}")
        self.tolerance = tolerance
