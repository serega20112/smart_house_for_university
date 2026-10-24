"""О чём просит климат дома.

Требование — решение модели, и способность, которая его удовлетворяет, — часть этого
решения. Увлажнение раньше писалось как «включить увлажнитель», из-за чего увлажнитель
с целевым уровнем становился невозможен; отдельное имя требования и его способности
держит эти два понятия врозь.
"""

from __future__ import annotations

from enum import StrEnum

from backend.domain.value_objects.climate.climate_band import ClimateBand
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability


class ClimateDemand(StrEnum):
    """Действие, нужное, чтобы вернуть климат в коридор."""

    COOL = "COOL"
    HEAT = "HEAT"
    HUMIDIFY = "HUMIDIFY"
    DEHUMIDIFY = "DEHUMIDIFY"

    @property
    def capability(self) -> Capability:
        """Возвращает способность, которая удовлетворяет требование.

        Returns:
            Capability: Способность, которую просят у устройства.
        """
        return DEMAND_CAPABILITIES[self]


DEMAND_CAPABILITIES: dict[ClimateDemand, Capability] = {
    ClimateDemand.COOL: Capability.COOL,
    ClimateDemand.HEAT: Capability.HEAT,
    ClimateDemand.HUMIDIFY: Capability.HUMIDIFY,
    ClimateDemand.DEHUMIDIFY: Capability.DEHUMIDIFY,
}

GOAL_TOLERANCE_CELSIUS = 0.5
"""Насколько измерению позволено не дойти до цели, чтобы её считали достигнутой.

Это бизнес-решение лежит рядом с остальными климатическими правилами, а не размазано
по агрегатам: сценарий и автоматика сходятся к одному порогу «дошли или нет».
"""


class DemandCalculator:
    """Превращает показания и настройку в порождённые ими требования.

    Вычислитель — сервис домена, а не набор функций, потому что для ответа нужны обе
    полосы климата и оба показания, и потому что вызывающему нельзя применить половину
    правила.
    """

    def demands_for(
        self,
        temperature_band: ClimateBand[Temperature] | None,
        humidity_band: ClimateBand[Humidity] | None,
        reading: ClimateReading,
    ) -> tuple[ClimateDemand, ...]:
        """Возвращает всякое требование, которое порождают нынешние показания.

        Отсутствующее измерение не порождает требования вместо догадки, и оба размера
        смотрятся даже когда настроен только один из них.

        Args:
            temperature_band: Допустимая полоса температуры или None, когда
                температуру автоматика не ведёт.
            humidity_band: Допустимая полоса влажности или None, когда влажность
                автоматика не ведёт.
            reading: Текущие показания датчиков.

        Returns:
            tuple[ClimateDemand, ...]: Требования к исполнению; пусто, когда каждое
            измерение уже внутри своей полосы.
        """
        demands: list[ClimateDemand] = []
        temperature = reading.temperature
        if temperature is not None and temperature_band is not None:
            if temperature_band.needs_decrease(temperature):
                demands.append(ClimateDemand.COOL)
            elif temperature_band.needs_increase(temperature):
                demands.append(ClimateDemand.HEAT)
        humidity = reading.humidity
        if humidity is not None and humidity_band is not None:
            if humidity_band.needs_increase(humidity):
                demands.append(ClimateDemand.HUMIDIFY)
            elif humidity_band.needs_decrease(humidity):
                demands.append(ClimateDemand.DEHUMIDIFY)
        return tuple(demands)

    def capability_towards(
        self, target_celsius: float, current_celsius: float | None
    ) -> Capability:
        """Возвращает способность, двигающая дом к целевой температуре.

        Без измерения просьбу считают охлаждением: обычно человек, называющий
        температуру, хочет в комнате прохладнее.

        Args:
            target_celsius: Запрошенная целевая температура.
            current_celsius: Измеренная температура или None, когда её нет.

        Returns:
            Capability: Охлаждение или нагрев.
        """
        if current_celsius is None or target_celsius < current_celsius:
            return Capability.COOL
        return Capability.HEAT
