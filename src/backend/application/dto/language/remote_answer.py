"""Одна структурированная команда, как её увидела удалённая модель."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RemoteAnswer:
    """То, что вернула машина, крутящая модели, в сыром виде её протокола.

    Attributes:
        intent_name: Название намерения или None, когда предложение не команда.
        confidence: Насколько уверена удалённая модель.
        device_name: Кусок имени устройства, найденный в предложении.
        device_kinds: Назначения устройств, о которых могло идти речь.
        capability: Способность, о которой просит предложение.
        temperature: Запрошенная температура, или None.
        humidity: Запрошенная влажность, или None.
        delay_minutes: Запрошенная задержка, или None.
        target: Запрошенное место, или None.
    """

    intent_name: str | None
    confidence: float
    device_name: str | None = None
    device_kinds: tuple[str, ...] = ()
    capability: str | None = None
    temperature: float | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None
