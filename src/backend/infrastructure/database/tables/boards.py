"""Строки платы, предложения о ней и её сети.

Декларативное описание всех таблиц реляционного хранилища.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.tables.base import Base


class EspDeviceRow(Base):
    """Плата, сопряжённая с одним аккаунтом.

    Attributes:
        id: Идентификатор, выданный агрегатом домена.
        user_id: Владелец платы.
        name: Имя, показанное человеку.
        pairing_key: Секрет, который плата предъявляет при соединении; он один на всю
            систему, потому что это и есть учётные данные платы.
        created_at: Момент сопряжения платы.
        last_seen_at: Момент последнего успешного handshake, или None.
        current_ssid: Сеть, о которой сообщила плата, или None.
    """

    __tablename__ = "esp_devices"
    __table_args__ = (Index("ix_esp_devices_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(60))
    pairing_key: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_ssid: Mapped[str | None] = mapped_column(String(32), nullable=True)


class EspClaimRow(Base):
    """Плата, которая объявила о себе и ждёт, что её заберёт аккаунт.

    Плата вправе объявить о себе не один раз, поэтому ключ устройства индексируют, а не
    делают уникальным: каждое объявление — своя строка со своим токеном.

    Attributes:
        id: Идентификатор, выданный агрегатом домена.
        device_key: Секрет, который плата предъявляет при соединении.
        label: Короткий код, показанный в интерфейсе.
        claim_token: Токен именно этого объявления; уникален, потому что его человек
            и вводит.
        announced_at: Момент, когда плата объявила о себе.
        expires_at: Момент, после которого предложение недействительно.
        claimed_by: Аккаунт, забравший предложение, или None пока оно открыто.
    """

    __tablename__ = "esp_claims"
    __table_args__ = (
        Index("ix_esp_claims_device_key", "device_key"),
        Index("ix_esp_claims_label", "label"),
        Index("ix_esp_claims_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    device_key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(8))
    claim_token: Mapped[str] = mapped_column(String(16), unique=True)
    announced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )


class BoardNetworkRow(Base):
    """Сеть, которую предписано использовать одной плате.

    Те же значения плата хранит у себя в памяти, а эта строка — копия, которую показывает
    интерфейс, и та же копия, которую плате отдают заново, когда она вернулась после
    изменения, которое сама применить не смогла. Пароль сети — секрет: он живёт здесь,
    потому что в таком случае плате его нужно выдать ещё раз, и с сервера в ответе он не
    уходит никогда.

    Attributes:
        board_id: Плата, к которой относится сеть.
        user_id: Владелец платы.
        ssid: Имя беспроводной сети.
        password: Пароль этой сети.
        host: Адрес сервера, которому плата докладывается.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт доски этого сервера.
        socket_path: Путь доски этого сервера.
        updated_at: Момент записи настроек.
    """

    __tablename__ = "board_networks"
    __table_args__ = (Index("ix_board_networks_user_id", "user_id"),)

    board_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("esp_devices.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    ssid: Mapped[str] = mapped_column(String(32))
    password: Mapped[str] = mapped_column(String(64))
    host: Mapped[str] = mapped_column(String(64))
    server_port: Mapped[int] = mapped_column(Integer)
    socket_port: Mapped[int] = mapped_column(Integer)
    socket_path: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
