"""Строки сценария, его действий и снятых до старта состояний.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.tables.base import Base


class ScenarioRow(Base):
    """Stored timed scenario of one account.

    Args:
        id: Identifier assigned by the domain aggregate.
        user_id: Owner of the scenario.
        status: Lifecycle stage, stored as text.
        created_at: Moment the scenario was asked for.
        start_at: Moment the scenario starts acting.
        duration_minutes: How long it may run, or None when it is unbounded.
        target: Area or object the user named, or None.
        completion_behavior: What happens with the devices afterwards, stored as
            text.
        version: Revision of the row, bumped on every update. A scenario that
            moves from an obsolete snapshot touches nothing instead of
            overwriting what an API call changed meanwhile.

    Returns:
        None.
    """

    __tablename__ = "scenarios"
    __table_args__ = (
        Index("ix_scenarios_user_id", "user_id"),
        Index("ix_scenarios_status", "status"),
        Index("ix_scenarios_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target: Mapped[str | None] = mapped_column(String(120), nullable=True)
    completion_behavior: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, default=0)


class ScenarioActionRow(Base):
    """One action performed when a scenario starts.

    Args:
        id: Identifier of the stored action, meaningful to the store only.
        scenario_id: Scenario the action belongs to.
        position: Zero based place of the action inside the scenario.
        capability: Capability the action asks for, stored as text.
        target_temperature: Temperature the action aims for, or None when it only
            switches something.

    Returns:
        None.
    """

    __tablename__ = "scenario_actions"
    __table_args__ = (Index("ix_scenario_actions_scenario_id", "scenario_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scenario_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("scenarios.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    capability: Mapped[str] = mapped_column(String(16))
    target_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)


class ScenarioCapturedStatusRow(Base):
    """State one device had before a scenario started.

    Args:
        scenario_id: Scenario the state was captured for.
        device_id: Device the state belongs to.
        status: State of the device, stored as text.

    Returns:
        None.
    """

    __tablename__ = "scenario_captured_statuses"

    scenario_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scenarios.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16))
