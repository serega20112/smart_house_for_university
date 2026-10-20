"""Declarative definition of every table of the relational store.

The schema exists only through the Alembic revisions in ``migrations/versions``.
Nothing in this package creates it, because a schema a deployment cannot replay
from zero is a schema nobody can reason about, and ``create_all`` hides exactly
the drift a review is supposed to catch.

Enumerations are stored as text. Every enumeration column is a plain ``String`` of
a fixed width, and the mappers of :mod:`smart_home.infrastructure.database.mappers`
translate between a value object and its textual value. No database enum type is
ever created, so adding a member to a ``StrEnum`` is a code change rather than a
migration, and a row written by one release stays readable by the next one.

Every identifier is a UUID taken from the domain: a row never invents the identity
of the aggregate it holds. Every table carrying user data has a ``user_id`` column
with a foreign key, so two accounts are kept apart by the store itself and not
only by the code that happens to query it.

Collections that used to be stored as opaque blobs are separate tables with real
foreign keys: capabilities, scenario actions, captured statuses, dashboard
widgets and automation participants. Deleting the aggregate that owns them deletes
them, so no row is left describing something that no longer exists.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base every table of the store is declared against."""


class UserRow(Base):
    """Stored account of one person.

    Args:
        id: Identifier assigned by the domain aggregate.
        email: Normalized login, unique across the whole system.
        password_hash: Stored form of the password, produced by the hasher and
            never inspected by the model.
        display_name: Name shown in the interface.
        created_at: Moment the account was created.

    Returns:
        None.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
