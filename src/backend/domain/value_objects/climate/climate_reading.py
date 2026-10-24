"""Снимок показаний датчиков климата в один момент."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature


@dataclass(frozen=True, slots=True)
class ClimateReading:
    """То, что датчики сообщили в последний раз.

    Поле отсутствует, а не равно нулю, когда плата не смогла измерить: автоматика
    различает «в комнате ровно ноль градусов» и «датчик не ответил».

    Attributes:
        temperature: Измеренная температура или None, если её нет.
        humidity: Измеренная относительная влажность или None, если её нет.
    """

    temperature: Temperature | None = None
    humidity: Humidity | None = None

    @property
    def is_usable(self) -> bool:
        """Сообщает, есть ли хотя бы одно годное измерение."""
        return self.temperature is not None or self.humidity is not None

    @classmethod
    def measured(cls, celsius: float | None, percent: float | None) -> ClimateReading:
        """Строит снимок из сырых чисел датчика.

        Args:
            celsius: Измеренная температура или None.
            percent: Измеренная относительная влажность или None.

        Returns:
            ClimateReading: Снимок с типами домена.
        """
        return cls(
            temperature=None if celsius is None else Temperature(celsius),
            humidity=None if percent is None else Humidity(percent),
        )
