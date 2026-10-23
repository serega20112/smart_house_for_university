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
    """Automation configuration of one account, stored as a single row.

    Args:
        user_id: Owner of the configuration and primary key of the row.
        enabled: Whether automation is active.
        target_temperature: Temperature the home is asked to hold.
        temperature_tolerance: How far the temperature may drift.
        target_humidity: Humidity the home is asked to hold.
        humidity_tolerance: How far the humidity may drift.
        version: Revision of the row, bumped on every save. A stale writer
            updates nothing instead of overwriting a newer configuration.

    Returns:
        None.
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
    """One device automation is allowed to drive.

    An account with no participant row drives every device that opted in, which is
    what the aggregate means by an empty set.

    Args:
        user_id: Owner of the configuration.
        device_id: Device taking part in automation.

    Returns:
        None.
    """

    __tablename__ = "automation_participants"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
