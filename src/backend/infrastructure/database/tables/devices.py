"""Строки логического устройства и его способностей.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.tables.base import Base


class DeviceRow(Base):
    """Stored configuration of one logical device owned by one account.

    Args:
        id: Identifier assigned by the domain aggregate.
        user_id: Owner of the device.
        name: Name shown to the user.
        kind: What the device is for, stored as text.
        channel: Relay channel the device is wired to.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device takes part in automation.
        version: Revision of the row, bumped on every update. A writer that has
            read an older revision updates nothing: the optimistic lock keeps a
            rehearsed command working on an obsolete snapshot from erasing a
            change somebody else committed meanwhile.

    Returns:
        None.
    """

    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "channel", name="uq_devices_user_id_channel"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(32))
    channel: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean)
    automation_enabled: Mapped[bool] = mapped_column(Boolean)
    version: Mapped[int] = mapped_column(Integer, default=0)


class DeviceCapabilityRow(Base):
    """One capability a logical device is able to perform.

    Args:
        device_id: Device the capability belongs to.
        capability: Capability name, stored as text.

    Returns:
        None.
    """

    __tablename__ = "device_capabilities"

    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    capability: Mapped[str] = mapped_column(String(16), primary_key=True)
