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

from backend.infrastructure.database.models.base import Base


class ScenarioModel(Base):
    """Сохранённый отложенный сценарий одного аккаунта.

    Attributes:
        id: Идентификатор, выданный агрегатом домена.
        user_id: Владелец сценария.
        status: Этап жизни, лежащий текстом.
        created_at: Момент, когда о сценарии попросили.
        start_at: Момент, когда сценарий начинает действовать.
        duration_minutes: Сколько ему разрешено идти, или None без границы.
        target: Место или предмет, который назвал человек, или None.
        completion_behavior: Что будет с устройствами после; лежит текстом.
        version: Ревизия строки, поднимаемая при каждой записи. Сценарий, идущий по
            устаревшему снимку, не трогает ничего вместо того, чтобы перетереть то, что
            успела изменить заявка API.
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


class ScenarioActionModel(Base):
    """Одно действие, выполняемое в момент начала сценария.

    Attributes:
        id: Идентификатор сохранённого действия, значимый только для хранилища.
        scenario_id: Сценарий, к которому относится действие.
        position: Место действия внутри сценария, считая от нуля.
        capability: Способность, о которой просит действие; лежит текстом.
        target_temperature: Температура, к которой действие идёт, или None, когда оно
            только что-то переключает.
    """

    __tablename__ = "scenario_actions"
    __table_args__ = (Index("ix_scenario_actions_scenario_id", "scenario_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scenario_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("scenarios.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    capability: Mapped[str] = mapped_column(String(16))
    target_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)


class ScenarioCapturedStatusModel(Base):
    """Состояние одного устройства до начала сценария.

    Attributes:
        scenario_id: Сценарий, ради которого состояние снимали.
        device_id: Устройство, к которому состояние относится.
        status: Состояние устройства, лежащее текстом.
    """

    __tablename__ = "scenario_captured_statuses"

    scenario_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scenarios.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16))
