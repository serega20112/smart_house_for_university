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
    """Сохранённая настройка одного логического устройства одного аккаунта.

    Attributes:
        id: Идентификатор, выданным агрегатом домена.
        user_id: Владелец устройства.
        name: Имя, показанное человеку.
        kind: Для чего устройство; лежит текстом.
        channel: Канал реле, к которому подключено устройство.
        enabled: Разрешено ли устройством управлять вообще.
        automation_enabled: Участвует ли устройство в автоматизации.
        version: Ревизия строки, поднимаемая при каждой записи. Кто прочитал
            старую ревизию, тот не обновляет ничего: оптимистичная блокировка не
            даёт отработанной команде стереть по устаревшему снимку изменение,
            которое тем временем кто-то закоммитил.
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
    """Одна способность, которую логическое устройство умеет выполнить.

    Attributes:
        device_id: Устройство, к которому относится способность.
        capability: Имя способности, лежащее текстом.
    """

    __tablename__ = "device_capabilities"

    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    capability: Mapped[str] = mapped_column(String(16), primary_key=True)
