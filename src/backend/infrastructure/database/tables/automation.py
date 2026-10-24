"""Строки настройки автоматизации и её участников.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.tables.base import Base


class AutomationRow(Base):
    """Настройка автоматизации одного аккаунта, лежащая одной строкой.

    Attributes:
        user_id: Владелец настройки и первичный ключ строки.
        enabled: Работает ли автоматизация.
        target_temperature: Температура, которую велено держать дому.
        temperature_tolerance: Насколько позволено уйти температуре.
        target_humidity: Влажность, которую велено держать дому.
        humidity_tolerance: Насколько позволено уйти влажности.
        version: Ревизия строки, поднимаемая при каждой записи. Устаревший
            записывающий не обновляет ничего, вместо того чтобы перетереть более новую
            настройку.
    """

    __tablename__ = "automation"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean)
    target_temperature: Mapped[float] = mapped_column(Float)
    temperature_tolerance: Mapped[float] = mapped_column(Float)
    target_humidity: Mapped[float] = mapped_column(Float)
    humidity_tolerance: Mapped[float] = mapped_column(Float)
    version: Mapped[int] = mapped_column(Integer, default=0)


class AutomationParticipantRow(Base):
    """Одно устройство, которым автоматизации разрешено управлять.

    Аккаунт без строк участников ведёт всякое устройство, которое на это согласилось, —
    именно это агрегат называет пустым множеством.

    Attributes:
        user_id: Владелец настройки.
        device_id: Устройство, участвующее в автоматизации.
    """

    __tablename__ = "automation_participants"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
