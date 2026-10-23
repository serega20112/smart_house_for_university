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
    """Board paired with one account.

    Args:
        id: Identifier assigned by the domain aggregate.
        user_id: Owner of the board.
        name: Name shown to the user.
        pairing_key: Secret the board presents while connecting, unique across
            the system because it is the credential of the board.
        created_at: Moment the board was paired.
        last_seen_at: Moment of the last successful handshake, or None.
        current_ssid: Network the board reported being on, or None.

    Returns:
        None.
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
    """Board that announced itself and waits for an account to take it.
    A board may announce itself more than once, so the device key is indexed
    rather than unique: every announcement is its own row with its own token.

    Args:
        id: Identifier assigned by the domain aggregate.
        device_key: Secret the board presents while connecting.
        label: Short code shown in the interface.
        claim_token: Token of this particular announcement, unique because it is
            what a person types.
        announced_at: Moment the board announced itself.
        expires_at: Moment the offer stops being valid.
        claimed_by: Account that took the offer, or None while it is open.

    Returns:
        None.
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
    """Network one board is told to use.

    The board keeps the same values in its own flash, and this row is the copy the
    interface shows and the copy the board is asked for again when it comes back
    after a change it could not apply. The password of the network is a secret: it
    lives here because the board has to be handed it one more time in that case,
    and it never leaves the server in an answer.

    Args:
        board_id: Board the network belongs to.
        user_id: Owner of the board.
        ssid: Name of the wireless network.
        password: Password of that network.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.
        updated_at: Moment the settings were written.

    Returns:
        None.
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
