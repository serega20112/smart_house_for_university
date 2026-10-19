"""Repositories binding the domain to the relational store.

All repositories live in one module because they are all the same thing: a thin
adapter around the one session the unit of work opened. Splitting them across
files would scatter the rules that are shared by every one of them.

Two rules hold for every repository here.

The first is that a repository never commits and never rolls back. The unit of
work owns the transaction, and a repository that rolled back would silently
discard the work of everything that ran before it in the same block. The single
exception is the translation of a unique violation on the login into
:mod:`backend.application.errors`: it re-raises a refusal of the application
layer and lets the unit of work do the rollback.

The second is that reading never writes. A lookup that finds nothing returns
``None`` instead of inserting a default row, so a screen that only looks at the
configuration cannot bring rows into existence behind the caller's back.

Every statement is executed as Core SQL against the tables of
:mod:`backend.infrastructure.database.tables`, and the values come from the pure
functions of :mod:`backend.infrastructure.database.mappers`. Nothing here builds
a domain aggregate by assigning to its fields, and nothing here lets the store
hand out an identity.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Table, delete, func, insert, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import EmailAlreadyTakenError
from backend.domain.accounts.user import User
from backend.domain.boards.board_network import BoardNetwork
from backend.domain.boards.esp_claim import EspClaim
from backend.domain.boards.esp_device import EspDevice
from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.identifiers import (
    DeviceId,
    EspClaimId,
    EspDeviceId,
    ScenarioId,
    UserId,
)
from backend.domain.personalization.dashboard_state import DashboardState
from backend.domain.personalization.user_preferences import UserPreferences
from backend.domain.scenarios.scenario import Scenario
from backend.domain.scenarios.scenario_action import ScenarioAction
from backend.domain.scenarios.scenario_status import ScenarioStatus
from backend.infrastructure.database import mappers
from backend.infrastructure.database.tables import (
    AutomationParticipantRow,
    AutomationRow,
    Base,
    BoardNetworkRow,
    DashboardRow,
    DashboardWidgetRow,
    DeviceCapabilityRow,
    DeviceRow,
    EspClaimRow,
    EspDeviceRow,
    PreferencesRow,
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
    UserRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


def is_unique_violation(error: IntegrityError) -> bool:
    """Return whether an integrity failure was a unique constraint violation.

    The SQL state class is the only part of the failure that stays the same across
    drivers, so it is the only thing the translation is allowed to look at.

    Args:
        error: Failure reported by the store.

    Returns:
        bool: True when the store refused a duplicate value.
    """
    return getattr(error.orig, "sqlstate", None) == UNIQUE_VIOLATION


async def first_row[Row: Base](
    runner: Runner, model: type[Row], *criteria: ColumnElement[bool]
) -> Row | None:
    """Return the single row a lookup selects, or None.

    Args:
        runner: Session or connection the lookup runs on.
        model: Mapped class to read.
        criteria: Restrictions of the lookup.

    Returns:
        Row | None: Row, or None when nothing matched.
    """
    result = await runner.execute(select(model).where(*criteria))
    return result.scalar_one_or_none()


async def every_row[Row: Base](
    runner: Runner, model: type[Row], *criteria: ColumnElement[bool]
) -> list[Row]:
    """Return every row a lookup selects.

    Args:
        runner: Session or connection the lookup runs on.
        model: Mapped class to read.
        criteria: Restrictions of the lookup.

    Returns:
        list[Row]: Matching rows.
    """
    result = await runner.execute(select(model).where(*criteria))
    return list(result.scalars().all())


async def insert_rows(runner: Runner, table: Table, rows: Sequence[Base]) -> None:
    """Write several rows of one table.

    Args:
        runner: Session or connection the write runs on.
        table: Table the rows belong to.
        rows: Rows to write.

    Returns:
        None.
    """
    if not rows:
        return
    await runner.execute(insert(table), [mappers.row_values(table, row) for row in rows])


def upsert_columns(table: Table, *frozen: str) -> dict[str, ColumnElement[object]]:
    """Return the columns an upsert refreshes when the row already exists.

    The named columns are left out on purpose: they are the key of the conflict,
    and writing them back would be meaningless.

    Args:
        table: Table whose columns are considered.
        frozen: Column names that must not be refreshed.

    Returns:
        dict[str, ColumnElement[object]]: Column name mapped to the value the
        conflicting insert proposed for it.
    """
    excluded = postgresql.insert(table).excluded
    untouched = set(frozen)
    return {
        column.name: excluded[column.name]
        for column in table.columns
        if column.name not in untouched
    }


async def capabilities_of(
    runner: Runner, device_ids: Sequence[UUID]
) -> dict[UUID, frozenset[Capability]]:
    """Return the capabilities of every device of a lookup.

    Args:
        runner: Session or connection the lookup runs on.
        device_ids: Devices the caller is about to return.

    Returns:
        dict[UUID, frozenset[Capability]]: Capabilities grouped by device.
    """
    if not device_ids:
        return {}
    result = await runner.execute(
        select(DeviceCapabilityRow.device_id, DeviceCapabilityRow.capability).where(
            DeviceCapabilityRow.device_id.in_(device_ids)
        )
    )
    grouped: dict[UUID, set[Capability]] = {}
    for device_id, capability in result.all():
        grouped.setdefault(device_id, set()).add(Capability.parse(capability))
    return {device_id: frozenset(values) for device_id, values in grouped.items()}


async def participants_of(runner: Runner, user_id: UserId) -> frozenset[DeviceId]:
    """Return the devices automation is allowed to drive.

    Args:
        runner: Session or connection the lookup runs on.
        user_id: Owner of the configuration.

    Returns:
        frozenset[DeviceId]: Participating devices, empty for every opted in one.
    """
    result = await runner.execute(
        select(AutomationParticipantRow.device_id).where(
            AutomationParticipantRow.user_id == user_id.value
        )
    )
    return frozenset(DeviceId.parse(value) for value in result.scalars().all())


class SqlAccountRepository:
    """Storage of the accounts of the system.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def add(self, user: User) -> None:
        """Store a new account.

        The uniqueness of the login is enforced by the store rather than by a
        lookup before the write, so two simultaneous registrations cannot both
        win. The failure is translated into a refusal of the application layer
        and the rollback is left to the unit of work.

        Args:
            user: Account to persist.

        Returns:
            None.

        Raises:
            EmailAlreadyTakenError: When the login is already registered.
        """
        values = mappers.row_values(UserRow.__table__, mappers.user_to_row(user))
        try:
            await self._session.execute(insert(UserRow.__table__).values(**values))
            await self._session.flush()
        except IntegrityError as error:
            if not is_unique_violation(error):
                raise
            raise EmailAlreadyTakenError(user.email.value) from error

    async def get(self, user_id: UserId) -> User | None:
        """Return an account by identifier.

        Args:
            user_id: Identifier of the account.

        Returns:
            User | None: Account, or None when it does not exist.
        """
        row = await first_row(self._session, UserRow, UserRow.id == user_id.value)
        return None if row is None else mappers.user_from_row(row)

    async def get_by_email(self, email: str) -> User | None:
        """Return an account by login.

        Args:
            email: Normalized login of the account.

        Returns:
            User | None: Account, or None when it does not exist.
        """
        row = await first_row(self._session, UserRow, UserRow.email == email)
        return None if row is None else mappers.user_from_row(row)


class SqlDeviceRepository:
    """Storage of the logical devices of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self, user_id: UserId) -> Sequence[Device]:
        """Return every device of an account.

        Args:
            user_id: Owner of the devices.

        Returns:
            Sequence[Device]: Configured devices.
        """
        rows = await every_row(self._session, DeviceRow, DeviceRow.user_id == user_id.value)
        stored = await capabilities_of(self._session, [row.id for row in rows])
        return [mappers.device_from_row(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> Device | None:
        """Return one device of an account.

        The lookup is scoped to the owner, so a device of another account reads as
        missing instead of being handed out.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            Device | None: Device, or None when the account has no such one.
        """
        row = await first_row(
            self._session,
            DeviceRow,
            DeviceRow.id == device_id.value,
            DeviceRow.user_id == user_id.value,
        )
        if row is None:
            return None
        stored = await capabilities_of(self._session, [row.id])
        return mappers.device_from_row(row, stored.get(row.id, frozenset()))

    async def add(self, device: Device) -> None:
        """Store a newly created device.

        The row of the device is written before its capabilities, because every
        capability row carries a foreign key to it.

        Args:
            device: Device to persist.

        Returns:
            None.
        """
        values = mappers.row_values(DeviceRow.__table__, mappers.device_to_row(device))
        await self._session.execute(insert(DeviceRow.__table__).values(**values))
        await insert_rows(
            self._session, DeviceCapabilityRow.__table__, mappers.capability_rows(device)
        )
        await self._session.flush()

    async def update(self, device: Device) -> None:
        """Store a changed device.

        The capabilities are replaced rather than merged: the aggregate holds the
        complete set, so a capability that is no longer listed was removed on
        purpose.

        Args:
            device: Device to persist.

        Returns:
            None.
        """
        row = mappers.device_to_row(device)
        await self._session.execute(
            update(DeviceRow)
            .where(DeviceRow.id == device.id.value, DeviceRow.user_id == device.user_id.value)
            .values(
                name=row.name,
                kind=row.kind,
                channel=row.channel,
                enabled=row.enabled,
                automation_enabled=row.automation_enabled,
            )
        )
        await self._session.execute(
            delete(DeviceCapabilityRow).where(DeviceCapabilityRow.device_id == device.id.value)
        )
        await insert_rows(
            self._session, DeviceCapabilityRow.__table__, mappers.capability_rows(device)
        )
        await self._session.flush()

    async def delete(self, user_id: UserId, device_id: DeviceId) -> bool:
        """Remove a device of an account.

        The capabilities, the automation participations and the dashboard entries
        pointing at the device are removed by the cascading foreign keys of the
        store, so no row survives describing something that no longer exists.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            bool: True when a device was removed.
        """
        result = await self._session.execute(
            delete(DeviceRow).where(
                DeviceRow.id == device_id.value, DeviceRow.user_id == user_id.value
            )
        )
        return bool(result.rowcount)

    async def channel_taken(
        self, user_id: UserId, channel: int, exclude: DeviceId | None = None
    ) -> bool:
        """Return whether a relay channel is already wired to another device.

        Args:
            user_id: Owner of the devices.
            channel: Physical relay channel.
            exclude: Device that is allowed to keep the channel.

        Returns:
            bool: True when another device of the account already uses it.
        """
        criteria: list[ColumnElement[bool]] = [
            DeviceRow.user_id == user_id.value,
            DeviceRow.channel == channel,
        ]
        if exclude is not None:
            criteria.append(DeviceRow.id != exclude.value)
        result = await self._session.execute(
            select(func.count()).select_from(DeviceRow).where(*criteria)
        )
        return bool(result.scalar_one())


class SqlScenarioRepository:
    """Storage of the timed scenarios of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self, user_id: UserId) -> Sequence[Scenario]:
        """Return every scenario of an account, newest first.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            Sequence[Scenario]: Stored scenarios.
        """
        result = await self._session.execute(
            select(ScenarioRow)
            .where(ScenarioRow.user_id == user_id.value)
            .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
        )
        return [await self._restore(row) for row in result.scalars().all()]

    async def list_holding_priority(self, user_id: UserId) -> Sequence[Scenario]:
        """Return the scenarios that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            Sequence[Scenario]: Pending and running scenarios.
        """
        holding = (ScenarioStatus.PENDING.value, ScenarioStatus.RUNNING.value)
        result = await self._session.execute(
            select(ScenarioRow)
            .where(
                ScenarioRow.user_id == user_id.value,
                ScenarioRow.status.in_(holding),
            )
            .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
        )
        return [await self._restore(row) for row in result.scalars().all()]

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> Scenario | None:
        """Return one scenario of an account.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            Scenario | None: Scenario, or None when the account has no such one.
        """
        row = await first_row(
            self._session,
            ScenarioRow,
            ScenarioRow.id == scenario_id.value,
            ScenarioRow.user_id == user_id.value,
        )
        return None if row is None else await self._restore(row)

    async def add(self, scenario: Scenario) -> None:
        """Store a newly scheduled scenario.

        Args:
            scenario: Scenario to persist.

        Returns:
            None.
        """
        values = mappers.row_values(ScenarioRow.__table__, mappers.scenario_to_row(scenario))
        await self._session.execute(insert(ScenarioRow.__table__).values(**values))
        await self._write_children(scenario)

    async def update(self, scenario: Scenario) -> None:
        """Store a changed scenario.

        The actions and the captured states are replaced rather than merged: the
        aggregate holds the complete collections, and a row that is no longer
        listed was deliberately removed from it.

        Args:
            scenario: Scenario to persist.

        Returns:
            None.
        """
        row = mappers.scenario_to_row(scenario)
        await self._session.execute(
            update(ScenarioRow)
            .where(
                ScenarioRow.id == scenario.id.value,
                ScenarioRow.user_id == scenario.user_id.value,
            )
            .values(
                status=row.status,
                created_at=row.created_at,
                start_at=row.start_at,
                duration_minutes=row.duration_minutes,
                target=row.target,
                completion_behavior=row.completion_behavior,
            )
        )
        await self._session.execute(
            delete(ScenarioActionRow).where(ScenarioActionRow.scenario_id == scenario.id.value)
        )
        await self._session.execute(
            delete(ScenarioCapturedStatusRow).where(
                ScenarioCapturedStatusRow.scenario_id == scenario.id.value
            )
        )
        await self._write_children(scenario)

    async def _restore(self, row: ScenarioRow) -> Scenario:
        """Rebuild one scenario together with its collections.

        Args:
            row: Row identifying the scenario.

        Returns:
            Scenario: Restored scenario.
        """
        action_rows = await every_row(
            self._session,
            ScenarioActionRow,
            ScenarioActionRow.scenario_id == row.id,
        )
        actions: tuple[ScenarioAction, ...] = tuple(
            mappers.action_from_row(entry)
            for entry in sorted(action_rows, key=lambda entry: entry.position)
        )
        captured_rows = await every_row(
            self._session,
            ScenarioCapturedStatusRow,
            ScenarioCapturedStatusRow.scenario_id == row.id,
        )
        captured: dict[DeviceId, DeviceStatus] = dict(
            mappers.captured_status_from_row(entry) for entry in captured_rows
        )
        return mappers.scenario_from_row(row, actions, captured)

    async def _write_children(self, scenario: Scenario) -> None:
        """Write the collection rows of one scenario.

        Args:
            scenario: Scenario whose collections are written.

        Returns:
            None.
        """
        await insert_rows(self._session, ScenarioActionRow.__table__, mappers.action_rows(scenario))
        await insert_rows(
            self._session,
            ScenarioCapturedStatusRow.__table__,
            mappers.captured_status_rows(scenario),
        )
        await self._session.flush()


class SqlAutomationRepository:
    """Storage of the automation configuration of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def get(self, user_id: UserId) -> AutomationSettings | None:
        """Return the stored configuration.

        An account that never configured automation has no row, and this returns
        None instead of creating one.

        Args:
            user_id: Owner of the configuration.

        Returns:
            AutomationSettings | None: Stored configuration, or None when the
            account never configured automation.
        """
        row = await first_row(self._session, AutomationRow, AutomationRow.user_id == user_id.value)
        if row is None:
            return None
        return mappers.automation_from_row(row, await participants_of(self._session, user_id))

    async def save(self, settings: AutomationSettings) -> None:
        """Store the automation configuration of an account.

        The row is written as an upsert, so storing the configuration twice in one
        session does not collide with itself.

        Args:
            settings: Configuration to persist.

        Returns:
            None.
        """
        values = mappers.row_values(AutomationRow.__table__, mappers.automation_to_row(settings))
        await self._session.execute(
            postgresql.insert(AutomationRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[AutomationRow.__table__.c.user_id],
                set_=upsert_columns(AutomationRow.__table__, "user_id"),
            )
        )
        await self._session.execute(
            delete(AutomationParticipantRow).where(
                AutomationParticipantRow.user_id == settings.user_id.value
            )
        )
        await insert_rows(
            self._session,
            AutomationParticipantRow.__table__,
            mappers.participant_rows(settings),
        )
        await self._session.flush()


class SqlPreferencesRepository:
    """Storage of the interface preferences of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def get(self, user_id: UserId) -> UserPreferences | None:
        """Return the stored preferences.

        Args:
            user_id: Owner of the preferences.

        Returns:
            UserPreferences | None: Stored preferences, or None when the account
            never changed them.
        """
        row = await first_row(
            self._session, PreferencesRow, PreferencesRow.user_id == user_id.value
        )
        return None if row is None else mappers.preferences_from_row(row)

    async def save(self, preferences: UserPreferences) -> None:
        """Store the preferences of an account.

        Args:
            preferences: Preferences to persist.

        Returns:
            None.
        """
        values = mappers.row_values(
            PreferencesRow.__table__, mappers.preferences_to_row(preferences)
        )
        await self._session.execute(
            postgresql.insert(PreferencesRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[PreferencesRow.__table__.c.user_id],
                set_=upsert_columns(PreferencesRow.__table__, "user_id"),
            )
        )
        await self._session.flush()


class SqlDashboardRepository:
    """Storage of the dashboard layout of one account.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def get(self, user_id: UserId) -> DashboardState | None:
        """Return the stored layout.

        Args:
            user_id: Owner of the layout.

        Returns:
            DashboardState | None: Stored layout, or None when the account never
            customized it.
        """
        row = await first_row(self._session, DashboardRow, DashboardRow.user_id == user_id.value)
        if row is None:
            return None
        widgets = await every_row(
            self._session,
            DashboardWidgetRow,
            DashboardWidgetRow.user_id == user_id.value,
        )
        return mappers.dashboard_from_row(row, widgets)

    async def save(self, dashboard: DashboardState) -> None:
        """Store the layout of an account.

        The marker row carries no column of its own, so writing it twice is a
        no-op rather than an update of nothing. The widgets are replaced
        wholesale, because the aggregate holds the complete ordered layout rather
        than a patch of it.

        Args:
            dashboard: Layout to persist.

        Returns:
            None.
        """
        values = mappers.row_values(DashboardRow.__table__, mappers.dashboard_to_row(dashboard))
        await self._session.execute(
            postgresql.insert(DashboardRow.__table__)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[DashboardRow.__table__.c.user_id])
        )
        await self._session.execute(
            delete(DashboardWidgetRow).where(DashboardWidgetRow.user_id == dashboard.user_id.value)
        )
        await insert_rows(
            self._session, DashboardWidgetRow.__table__, mappers.widget_rows(dashboard)
        )
        await self._session.flush()


class SqlBoardRepository:
    """Storage of the boards paired with accounts.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def add(self, board: EspDevice) -> None:
        """Store a newly paired board.

        Args:
            board: Board to persist.

        Returns:
            None.
        """
        values = mappers.row_values(EspDeviceRow.__table__, mappers.board_to_row(board))
        await self._session.execute(insert(EspDeviceRow.__table__).values(**values))
        await self._session.flush()

    async def list_for(self, user_id: UserId) -> Sequence[EspDevice]:
        """Return every board of an account.

        Args:
            user_id: Owner of the boards.

        Returns:
            Sequence[EspDevice]: Boards of the account.
        """
        result = await self._session.execute(
            select(EspDeviceRow)
            .where(EspDeviceRow.user_id == user_id.value)
            .order_by(EspDeviceRow.created_at, EspDeviceRow.id)
        )
        return [mappers.board_from_row(row) for row in result.scalars().all()]

    async def get(self, user_id: UserId, board_id: EspDeviceId) -> EspDevice | None:
        """Return one board of an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            EspDevice | None: Board, or None when the account has no such one.
        """
        row = await first_row(
            self._session,
            EspDeviceRow,
            EspDeviceRow.id == board_id.value,
            EspDeviceRow.user_id == user_id.value,
        )
        return None if row is None else mappers.board_from_row(row)

    async def get_by_key(self, pairing_key: str) -> EspDevice | None:
        """Return the board presenting a pairing key.

        This is the lookup the board handshake resolves before anything else: the
        key the board presents is what turns a connection into a home.

        Args:
            pairing_key: Secret presented during the handshake.

        Returns:
            EspDevice | None: Board, or None when the key is unknown.
        """
        row = await first_row(self._session, EspDeviceRow, EspDeviceRow.pairing_key == pairing_key)
        return None if row is None else mappers.board_from_row(row)

    async def mark_seen(
        self, board_id: EspDeviceId, seen_at: datetime, ssid: str | None = None
    ) -> None:
        """Record that a board has just connected.

        Only the timestamp and the network are written. The board is not read
        first and is not written back whole, so two handshakes of the same board
        cannot overwrite each other's configuration.

        Args:
            board_id: Identifier of the board.
            seen_at: Moment of the successful handshake.
            ssid: Network the board reported being on, or None when it did not
                report one and the previous answer stays.

        Returns:
            None.
        """
        values: dict[str, object] = {"last_seen_at": seen_at}
        if ssid is not None:
            values["current_ssid"] = ssid
        await self._session.execute(
            update(EspDeviceRow).where(EspDeviceRow.id == board_id.value).values(**values)
        )
        await self._session.flush()

    async def delete(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Remove a board of an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when a board was removed.
        """
        result = await self._session.execute(
            delete(EspDeviceRow).where(
                EspDeviceRow.id == board_id.value, EspDeviceRow.user_id == user_id.value
            )
        )
        return bool(result.rowcount)


class SqlClaimRepository:
    """Storage of the boards that announced themselves and wait for an owner.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """
    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def add(self, claim: EspClaim) -> None:
        """Store a new offer.

        Args:
            claim: Offer to persist.

        Returns:
            None.
        """
        values = mappers.row_values(EspClaimRow.__table__, mappers.claim_to_row(claim))
        await self._session.execute(insert(EspClaimRow.__table__).values(**values))
        await self._session.flush()

    async def get_by_key(self, device_key: str) -> EspClaim | None:
        """Return the newest open offer of a board.

        Args:
            device_key: Secret the board presents while connecting.

        Returns:
            EspClaim | None: Offer, or None when the board never announced itself.
        """
        result = await self._session.execute(
            select(EspClaimRow)
            .where(EspClaimRow.device_key == device_key, EspClaimRow.claimed_by.is_(None))
            .order_by(EspClaimRow.announced_at.desc(), EspClaimRow.id)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else mappers.claim_from_row(row)

    async def get_by_token(self, claim_token: str) -> EspClaim | None:
        """Return the offer of a token.

        A token that was already used still resolves, so the caller can tell a
        stale offer from a made up one instead of both reading as unknown.

        Args:
            claim_token: Token shown in the interface.

        Returns:
            EspClaim | None: Offer, or None when the token is unknown.
        """
        row = await first_row(self._session, EspClaimRow, EspClaimRow.claim_token == claim_token)
        return None if row is None else mappers.claim_from_row(row)

    async def list_open(self) -> Sequence[EspClaim]:
        """Return every offer nobody took yet.

        This is a plain read: it never removes anything, not even an offer that is
        already over. Purging what expired is a separate command.

        Returns:
            Sequence[EspClaim]: Open offers.
        """
        result = await self._session.execute(
            select(EspClaimRow)
            .where(EspClaimRow.claimed_by.is_(None))
            .order_by(EspClaimRow.announced_at.desc(), EspClaimRow.id)
        )
        return [mappers.claim_from_row(row) for row in result.scalars().all()]

    async def take(self, claim_id: EspClaimId, user_id: UserId) -> bool:
        """Record conditionally that an account took the offer.

        The condition lives in the statement itself, so the store decides the
        winner of a race instead of this code deciding it from a value it read a
        moment earlier. The loser of the race sees False and changes nothing.

        Args:
            claim_id: Identifier of the offer.
            user_id: Account taking the board.

        Returns:
            bool: True when this call was the one that claimed it.
        """
        result = await self._session.execute(
            update(EspClaimRow)
            .where(EspClaimRow.id == claim_id.value, EspClaimRow.claimed_by.is_(None))
            .values(claimed_by=user_id.value)
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def delete_expired(self, before: datetime) -> int:
        """Remove the offers that are over.

        This is a command and never a side effect of reading.

        Args:
            before: Moment the offers have to be older than.

        Returns:
            int: Number of removed offers.
        """
        result = await self._session.execute(
            delete(EspClaimRow).where(EspClaimRow.expires_at < before)
        )
        return int(result.rowcount or 0)


class SqlBoardNetworkRepository:
    """Storage of the network each board is told to use.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def get(self, board_id: EspDeviceId) -> BoardNetwork | None:
        """Return the network of one board.

        Args:
            board_id: Identifier of the board.

        Returns:
            BoardNetwork | None: Network of that board, or None when it was
            never configured.
        """
        row = await first_row(
            self._session, BoardNetworkRow, BoardNetworkRow.board_id == board_id.value
        )
        return None if row is None else mappers.network_from_row(row)

    async def save(self, network: BoardNetwork) -> None:
        """Store the network of a board.

        The row is written whole, so a change of any of the values replaces the
        previous ones instead of leaving a part of the old network behind.

        Args:
            network: Network to persist.

        Returns:
            None.
        """
        values = mappers.row_values(BoardNetworkRow.__table__, mappers.network_to_row(network))
        await self._session.execute(
            postgresql.insert(BoardNetworkRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[BoardNetworkRow.__table__.c.board_id],
                set_=upsert_columns(BoardNetworkRow.__table__, "board_id", "user_id"),
            )
        )
        await self._session.flush()

    async def delete(self, board_id: EspDeviceId) -> bool:
        """Remove the network of a board.

        Args:
            board_id: Identifier of the board.

        Returns:
            bool: True when a network was removed.
        """
        result = await self._session.execute(
            delete(BoardNetworkRow).where(BoardNetworkRow.board_id == board_id.value)
        )
        return bool(result.rowcount)
