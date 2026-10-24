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

from backend.infrastructure.database.models.base import Base


class PreferencesModel(Base):
    """Настройки интерфейса одного аккаунта, лежащие одной строкой.

    Attributes:
        user_id: Владелец настроек и первичный ключ строки.
        temperature_unit: Единица, в которой показывают климат.
        theme: Визуальная тема.
        language: Язык интерфейса.
        show_command_chat: Показывать ли чат команд на главном экране.
    """

    __tablename__ = "preferences"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    temperature_unit: Mapped[str] = mapped_column(String(2))
    theme: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(8))
    show_command_chat: Mapped[bool] = mapped_column(Boolean)


class DashboardModel(Base):
    """Раскладка главного экрана одного аккаунта, лежащая одной строкой.

    Сама строка карточек не несёт: они живут в ``dashboard_widgets``, чтобы каждая была
    адресуема, упорядочена и защищена ссылкой. Строка нужна только для того, чтобы
    отсутствие раскладки оставалось наблюдаемым фактом.

    Attributes:
        user_id: Владелец раскладки и первичный ключ строки.
    """

    __tablename__ = "dashboard"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class DashboardWidgetModel(Base):
    """Одна карточка раскладки главного экрана.

    Attributes:
        id: Идентификатор сохранённой карточки, значимый только для хранилища.
        user_id: Владелец раскладки.
        position: Место карточки в порядке вывода, считая от нуля.
        kind: Какой готовый компонент рисовать; лежит текстом.
        device_id: Устройство, которым карточку питают, или None для общей.
        title: Личный заголовок поверх значения по умолчанию.
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
