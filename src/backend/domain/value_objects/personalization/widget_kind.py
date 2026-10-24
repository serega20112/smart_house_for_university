"""Компонент, который виджет главного экрана рисует."""

from __future__ import annotations

from enum import StrEnum


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
            ValueError: Когда значение не называет вид компонента.
        """
        if isinstance(raw, cls):
            return raw
        if raw is None:
            raise ValueError("widget kind is missing")
        return cls(str(raw).strip().lower())
