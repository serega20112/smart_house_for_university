"""Значения климата в том виде, в каком их показывает экран."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadingView:
    """Измеренные значения климата для интерфейса.

    Attributes:
        temperature: Измеренная температура или None.
        humidity: Измеренная относительная влажность или None.
    """

    temperature: float | None = None
    humidity: float | None = None
