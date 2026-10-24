"""Компонент, который виджет главного экрана рисует."""

from __future__ import annotations

from enum import StrEnum

from backend.domain.exceptions.personalization import InvalidWidgetKindError


class WidgetKind(StrEnum):
    """Готовый компонент, который интерфейс умеет нарисовать сам."""

    CLIMATE = "climate"
    SENSOR = "sensor"
    DEVICE = "device"
    COMMAND = "command"

    @classmethod
    def parse(cls, raw: object) -> WidgetKind:
        """Читает вид компонента из значения, пришедшего извне.

        Args:
            raw: Имя вида или его член перечисления.

        Returns:
            WidgetKind: Прочитанный вид.

        Raises:
            InvalidWidgetKindError: Когда значение не называет вид компонента.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise InvalidWidgetKindError(raw)
        try:
            return cls(str(raw).strip().lower())
        except ValueError as error:
            raise InvalidWidgetKindError(raw) from error
