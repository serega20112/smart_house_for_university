"""Строки настроек человека и разметки его дашборда.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.tables.base import Base


class PreferencesRow(Base):
    """Interface preferences of one account, stored as a single row.

    Args:
        user_id: Owner of the preferences and primary key of the row.
        temperature_unit: Unit climate values are rendered in.
        theme: Visual theme.
        language: Interface language.
        show_command_chat: Whether the command chat is shown on the dashboard.

    Returns:
        None.
    """

    __tablename__ = "preferences"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    temperature_unit: Mapped[str] = mapped_column(String(2))
    theme: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(8))
    show_command_chat: Mapped[bool] = mapped_column(Boolean)


class DashboardRow(Base):
    """Dashboard layout of one account, stored as a single row.

    The row itself carries no widgets: they live in ``dashboard_widgets`` so that
    every entry is addressable, ordered and referentially protected. The row
    exists only to make the absence of a layout an observable fact.

    Args:
        user_id: Owner of the layout and primary key of the row.

    Returns:
        None.
    """

    __tablename__ = "dashboard"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class DashboardWidgetRow(Base):
    """One entry of a dashboard layout.

    Args:
        id: Identifier of the stored entry, meaningful to the store only.
        user_id: Owner of the layout.
        position: Zero based render order of the entry.
        kind: Which generic component to draw, stored as text.
        device_id: Device feeding the component, or None for a global one.
        title: Personal title overriding the component default.

    Returns:
        None.
    """

    __tablename__ = "dashboard_widgets"
    __table_args__ = (Index("ix_dashboard_widgets_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    device_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(60), nullable=True)
