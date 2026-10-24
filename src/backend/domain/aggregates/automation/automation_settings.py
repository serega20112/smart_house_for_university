"""Настройка автоматизации одного аккаунта.

Это собственный агрегат: он владеет целью, допуском вокруг неё и списком
участников. Любое изменение идёт через метод, который проверяет значения и
записывает факт, поэтому сценарий приложения не может ни переключить признак
присваиванием, ни построить недостижимый коридор.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from backend.domain.events import AutomationSettingsChanged
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.climate_band import ClimateBand
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.climate.tolerance import Tolerance

DEFAULT_TARGET_TEMPERATURE_C = 22.0
DEFAULT_TEMPERATURE_TOLERANCE_C = 1.0
DEFAULT_TARGET_HUMIDITY_PERCENT = 45.0
DEFAULT_HUMIDITY_TOLERANCE_PERCENT = 5.0


@dataclass
class AutomationSettings:
    """Цели и допуски, к которым стремится климатическая автоматизация.

    Attributes:
        user_id: Владелец настройки.
        enabled: Работает ли автоматизация.
        target_temperature: Температуру, которую велено держать дому.
        temperature_tolerance: Насколько температуре позволено уйти, прежде чем
            примутся за устройство.
        target_humidity: Влажность, которую велено держать дому.
        humidity_tolerance: Насколько позволено уйти влажности.
        participating_device_ids: Устройства-участники; пустое множество значит
            каждое устройство, которое само на это согласилось.
    """

    user_id: UserId
    enabled: bool = False
    target_temperature: Temperature = field(
        default_factory=lambda: Temperature(DEFAULT_TARGET_TEMPERATURE_C)
    )
    temperature_tolerance: float = DEFAULT_TEMPERATURE_TOLERANCE_C
    target_humidity: Humidity = field(
        default_factory=lambda: Humidity(DEFAULT_TARGET_HUMIDITY_PERCENT)
    )
    humidity_tolerance: float = DEFAULT_HUMIDITY_TOLERANCE_PERCENT
    participating_device_ids: frozenset[DeviceId] = field(default_factory=frozenset)
    version: int = 0
    _events: list[AutomationSettingsChanged] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Проверяет оба допуска, чтобы потом их не починял каждый читатель.

        Raises:
            InvalidToleranceError: Когда допуск отрицательный или слишком большой.
        """
        Tolerance(self.temperature_tolerance)
        Tolerance(self.humidity_tolerance)

    @property
    def temperature_band(self) -> ClimateBand[Temperature]:
        """Возвращает допустимый коридор температуры."""
        return ClimateBand(self.target_temperature, self.temperature_tolerance)

    @property
    def humidity_band(self) -> ClimateBand[Humidity]:
        """Возвращает допустимый коридор влажности."""
        return ClimateBand(self.target_humidity, self.humidity_tolerance)

    def device_participates(self, device_id: DeviceId) -> bool:
        """Сообщает, вправе ли автоматизация вести это устройство.

        Args:
            device_id: Идентификатор устройства.

        Returns:
            bool: True, когда устройство участвует в автоматизации.
        """
        if not self.participating_device_ids:
            return True
        return device_id in self.participating_device_ids

    def enable(self) -> None:
        """Включает автоматику."""
        self._set_enabled(True)

    def disable(self) -> None:
        """Выключает автоматику."""
        self._set_enabled(False)

    def aim_at_temperature(self, target: Temperature, tolerance: float | None = None) -> None:
        """Меняет температуру, которую велено держать дому.

        Новые значения проверяются до записи, поэтому отвергнутый допуск оставляет
        настройку ровно такой, какой она была.

        Args:
            target: Новая целевая температура.
            tolerance: Новый допуск или None, чтобы оставить прежний.

        Raises:
            InvalidToleranceError: Когда новый допуск отрицательный или велик.
        """
        checked = self._checked_tolerance(tolerance, self.temperature_tolerance)
        self.target_temperature = target
        self.temperature_tolerance = checked
        self._record()

    def aim_at_humidity(self, target: Humidity, tolerance: float | None = None) -> None:
        """Меняет влажность, которую велено держать дому.

        Новые значения проверяются до записи, поэтому отвергнутый допуск оставляет
        настройку ровно такой, какой она была.

        Args:
            target: Новая целевая влажность.
            tolerance: Новый допуск или None, чтобы оставить прежний.

        Raises:
            InvalidToleranceError: Когда новый допуск отрицательный или велик.
        """
        checked = self._checked_tolerance(tolerance, self.humidity_tolerance)
        self.target_humidity = target
        self.humidity_tolerance = checked
        self._record()

    def set_participants(self, device_ids: frozenset[DeviceId]) -> None:
        """Выбирает устройства, которыми автоматизации разрешено управлять.

        Args:
            device_ids: Участники или пустое множество ради каждого согласившегося.
        """
        self.participating_device_ids = frozenset(device_ids)
        self._record()

    def pull_events(self) -> tuple[AutomationSettingsChanged, ...]:
        """Возвращает записанные факты и забывает их.

        Returns:
            tuple[AutomationSettingsChanged, ...]: Факты с прошлого обращения.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def _set_enabled(self, enabled: bool) -> None:
        if self.enabled is enabled:
            return
        self.enabled = enabled
        self._record()

    @staticmethod
    def _checked_tolerance(requested: float | None, current: float) -> float:
        """Возвращает заведомо допустимый допуск.

        Args:
            requested: Допуск, о котором просили, или None оставить нынешний.
            current: Допуск, который сохранён сейчас.

        Returns:
            float: Проверенная ширина коридора.

        Raises:
            InvalidToleranceError: Когда запрошенный допуск отрицательный или велик.
        """
        if requested is None:
            return Tolerance(current).value
        return Tolerance(requested).value

    def _record(self) -> None:
        self._events.append(AutomationSettingsChanged(user_id=self.user_id))

    @classmethod
    def create(cls, user_id: UserId) -> Self:
        """Строит настройку, с которой начинает свежий аккаунт.

        Args:
            user_id: Владелец настройки.

        Returns:
            Self: Настройка по умолчанию с выключенной автоматизацией.
        """
        return cls(user_id=user_id)
