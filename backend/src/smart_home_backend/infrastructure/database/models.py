"""SQLAlchemy models.

Persistence details stay in the infrastructure layer; domain entities reach the
database through the mappers of this package.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

AUTOMATION_SINGLETON_ID = 1


class Base(DeclarativeBase):
    """Declarative base of every model."""


class DeviceRow(Base):
    """Stored configuration of a logical device."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(40))
    physical_channel: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AutomationRow(Base):
    """Single row holding the automation configuration."""

    __tablename__ = "automation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=AUTOMATION_SINGLETON_ID)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    target_temperature: Mapped[float] = mapped_column(Float, default=22.0)
    temperature_tolerance: Mapped[float] = mapped_column(Float, default=1.0)
    target_humidity: Mapped[float] = mapped_column(Float, default=45.0)
    humidity_tolerance: Mapped[float] = mapped_column(Float, default=5.0)
    participating_device_ids: Mapped[list] = mapped_column(JSON, default=list)


class ScenarioRow(Base):
    """Stored timed scenario."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    completion_behavior: Mapped[str] = mapped_column(String(32))
    restore_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
