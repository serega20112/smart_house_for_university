"""Read side of the store.

A query object answers one question and returns a read model shaped for its
consumer, never an aggregate. That is the whole reason the read side exists: a
screen never opens a transaction and never has to walk a device, a scenario or a
board to draw it.

Every query runs plain selects on an engine and never begins a transaction of its
own. Reading the configuration of a home is not a decision anybody has to be able
to undo, and a select wrapped in a transaction only buys overhead and a longer
lived snapshot.

Two values of a read model cannot come from a table row and are therefore filled
in with the state a freshly wired device is assumed to have: the logical status of
a device and whether a board is connected right now. Both belong to the live layer
of the hardware, not to the relational store.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.devices.capability import Capability
from backend.domain.devices.device_kind import DeviceKind
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.identifiers import (
    DeviceId,
    EspClaimId,
    EspDeviceId,
    ScenarioId,
    UserId,
)
from backend.domain.scenarios.scenario_action import ScenarioAction
from backend.domain.scenarios.scenario_status import ScenarioStatus
from backend.domain.value_objects.account.account_profile import AccountProfile
from backend.domain.value_objects.account.stored_credentials import StoredCredentials
from backend.domain.value_objects.automation.automation_view import AutomationView
from backend.domain.value_objects.boards.board_claim_view import BoardClaimView
from backend.domain.value_objects.boards.board_view import BoardView
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.domain.value_objects.scenario.scenario_view import ScenarioView
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories import (
    capabilities_of,
    every_row,
    first_row,
    participants_of,
)
from backend.infrastructure.database.tables import (
    AutomationRow,
    DeviceRow,
    EspClaimRow,
    EspDeviceRow,
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
    UserRow,
)

HOLDING_STAGES = (ScenarioStatus.PENDING.value, ScenarioStatus.RUNNING.value)


class SqlAccountQueries:
    """Reads of the accounts, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def get_profile(self, user_id: UserId) -> AccountProfile | None:
        """Return the profile of an account.

        Args:
            user_id: Owner of the account.

        Returns:
            AccountProfile | None: Profile, or None when the account is gone.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, UserRow, UserRow.id == user_id.value)
        if row is None:
            return None
        return AccountProfile(
            id=UserId.parse(row.id),
            email=row.email,
            display_name=row.display_name,
            created_at=mappers.as_utc(row.created_at),
        )

    async def get_credentials(self, email: str) -> StoredCredentials | None:
        """Return the credentials a login belongs to.

        The stored password is the only thing read here: the profile of the
        account is a separate question with a separate answer.

        Args:
            email: Normalized login of the account.

        Returns:
            StoredCredentials | None: Credentials, or None when no account uses
            that login.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, UserRow, UserRow.email == email)
        if row is None:
            return None
        return StoredCredentials(user_id=UserId.parse(row.id), password_hash=row.password_hash)

    async def list_registered_ids(self) -> list[UserId]:
        """Return the identifiers of every registered account.

        Returns:
            list[UserId]: Registered accounts.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(select(UserRow.id).order_by(UserRow.id))
            return [UserId.parse(value) for value in result.scalars().all()]


class SqlDeviceQueries:
    """Reads of the device configuration, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[DeviceView]:
        """Return every device of an account.

        Args:
            user_id: Owner of the devices.

        Returns:
            list[DeviceView]: Devices shaped for display.
        """
        async with self._engine.connect() as connection:
            rows = await every_row(connection, DeviceRow, DeviceRow.user_id == user_id.value)
            stored = await capabilities_of(connection, [row.id for row in rows])
        return [device_view_of(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> DeviceView | None:
        """Return one device of an account.

        Args:
            user_id: Owner of the device.
            device_id: Identifier of the device.

        Returns:
            DeviceView | None: Device, or None when the account has no such one.
        """
        async with self._engine.connect() as connection:
            row = await first_row(
                connection,
                DeviceRow,
                DeviceRow.id == device_id.value,
                DeviceRow.user_id == user_id.value,
            )
            if row is None:
                return None
            stored = await capabilities_of(connection, [row.id])
        return device_view_of(row, stored.get(row.id, frozenset()))


class SqlAutomationQueries:
    """Reads of the automation configuration, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def get(self, user_id: UserId) -> AutomationView:
        """Return the automation configuration of an account.

        An account that never configured automation still gets an answer: the
        defaults are taken from the aggregate itself, so the read model can never
        drift away from the values a fresh home is actually built with.

        Args:
            user_id: Owner of the configuration.

        Returns:
            AutomationView: Configuration shaped for display.
        """
        async with self._engine.connect() as connection:
            row = await first_row(connection, AutomationRow, AutomationRow.user_id == user_id.value)
            participants = await participants_of(connection, user_id)
        if row is None:
            return automation_view_of(AutomationSettings.create(user_id), frozenset())
        return automation_view_of(mappers.automation_from_row(row, participants), participants)


class SqlScenarioQueries:
    """Reads of the timed scenarios, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[ScenarioView]:
        """Return every scenario of an account.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Scenarios shaped for display.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(ScenarioRow)
                .where(ScenarioRow.user_id == user_id.value)
                .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
            )
            rows = result.scalars().all()
            return [await scenario_view_of(connection, row) for row in rows]

    async def list_holding_priority(self, user_id: UserId) -> list[ScenarioView]:
        """Return the scenarios that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Pending and running scenarios.
        """
        return await self._holding(user_id)

    async def get(self, user_id: UserId, scenario_id: ScenarioId) -> ScenarioView | None:
        """Return one scenario of an account.

        Args:
            user_id: Owner of the scenario.
            scenario_id: Identifier of the scenario.

        Returns:
            ScenarioView | None: Scenario, or None when the account has no such
            one.
        """
        async with self._engine.connect() as connection:
            row = await first_row(
                connection,
                ScenarioRow,
                ScenarioRow.id == scenario_id.value,
                ScenarioRow.user_id == user_id.value,
            )
            if row is None:
                return None
            return await scenario_view_of(connection, row)

    async def latest_holding_priority(self, user_id: UserId) -> ScenarioView | None:
        """Return the most recently scheduled scenario still holding priority.

        Choosing it is a property of the stored data, ordered by the moment the
        scenario was asked for, rather than a guess about the order of a list. Only
        the newest row is fetched, so the answer costs the same whether the home
        holds one scenario or a hundred.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            ScenarioView | None: Matching scenario, or None when there is none.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(ScenarioRow)
                .where(
                    ScenarioRow.user_id == user_id.value,
                    ScenarioRow.status.in_(HOLDING_STAGES),
                )
                .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return await scenario_view_of(connection, row)

    async def _holding(self, user_id: UserId) -> list[ScenarioView]:
        """Return the scenarios of an account that still outrank automation.

        Args:
            user_id: Owner of the scenarios.

        Returns:
            list[ScenarioView]: Pending and running scenarios, newest first.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(ScenarioRow)
                .where(
                    ScenarioRow.user_id == user_id.value,
                    ScenarioRow.status.in_(HOLDING_STAGES),
                )
                .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id)
            )
            rows = result.scalars().all()
            return [await scenario_view_of(connection, row) for row in rows]


class SqlBoardQueries:
    """Reads of the boards, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[BoardView]:
        """Return every board of an account.

        Args:
            user_id: Owner of the boards.

        Returns:
            list[BoardView]: Boards shaped for display.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(EspDeviceRow)
                .where(EspDeviceRow.user_id == user_id.value)
                .order_by(EspDeviceRow.created_at, EspDeviceRow.id)
            )
            return [board_view_of(row) for row in result.scalars().all()]

    async def list_open_claims(self) -> list[BoardClaimView]:
        """Return every offer nobody took yet.

        Reading the list never deletes anything: an offer that is already over is
        still listed, and removing it is a separate command.

        Returns:
            list[BoardClaimView]: Open offers.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(EspClaimRow)
                .where(EspClaimRow.claimed_by.is_(None))
                .order_by(EspClaimRow.announced_at.desc(), EspClaimRow.id)
            )
            return [claim_view_of(row) for row in result.scalars().all()]


def device_view_of(row: DeviceRow, capabilities: frozenset[Capability]) -> DeviceView:
    """Return the read model of one stored device.

    The device is reported as off because its logical state belongs to the live
    layer of the hardware, not to a table row.

    Args:
        row: Row to shape.
        capabilities: Capabilities read from the capability table.

    Returns:
        DeviceView: Device shaped for display.
    """
    return DeviceView(
        id=DeviceId.parse(row.id),
        name=row.name,
        kind=DeviceKind.parse(row.kind),
        channel=row.channel,
        capabilities=capabilities,
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
        status=DeviceStatus.OFF,
    )


def automation_view_of(
    settings: AutomationSettings, participants: frozenset[DeviceId]
) -> AutomationView:
    """Return the read model of one automation configuration.

    Args:
        settings: Configuration to shape.
        participants: Devices automation is allowed to drive.

    Returns:
        AutomationView: Configuration shaped for display.
    """
    return AutomationView(
        enabled=settings.enabled,
        target_temperature=settings.target_temperature.celsius,
        target_humidity=settings.target_humidity.percent,
        temperature_tolerance=settings.temperature_tolerance,
        humidity_tolerance=settings.humidity_tolerance,
        participating_device_ids=participants,
    )


async def scenario_view_of(connection: AsyncConnection, row: ScenarioRow) -> ScenarioView:
    """Return the read model of one stored scenario.

    Args:
        connection: Connection the read is executed on.
        row: Row to shape.

    Returns:
        ScenarioView: Scenario shaped for display.
    """
    scenario = mappers.scenario_from_row(
        row,
        await scenario_actions_of(connection, row),
        await captured_statuses_of(connection, row),
    )
    return ScenarioView(
        id=scenario.id,
        status=scenario.status,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior,
        actions=scenario.actions,
    )


async def scenario_actions_of(
    connection: AsyncConnection, row: ScenarioRow
) -> tuple[ScenarioAction, ...]:
    """Return the actions of one stored scenario in the order it declares.

    Args:
        connection: Connection the read is executed on.
        row: Row identifying the scenario.

    Returns:
        tuple[ScenarioAction, ...]: Actions of the scenario.
    """
    stored = await every_row(
        connection,
        ScenarioActionRow,
        ScenarioActionRow.scenario_id == row.id,
    )
    ordered = sorted(stored, key=lambda entry: entry.position)
    return tuple(mappers.action_from_row(entry) for entry in ordered)


async def captured_statuses_of(
    connection: AsyncConnection, row: ScenarioRow
) -> dict[DeviceId, DeviceStatus]:
    """Return the device states captured before one scenario started.

    Args:
        connection: Connection the read is executed on.
        row: Row identifying the scenario.

    Returns:
        dict[DeviceId, DeviceStatus]: Device identifiers mapped to the state
        they had.
    """
    stored = await every_row(
        connection,
        ScenarioCapturedStatusRow,
        ScenarioCapturedStatusRow.scenario_id == row.id,
    )
    return dict(mappers.captured_status_from_row(entry) for entry in stored)


def board_view_of(row: EspDeviceRow) -> BoardView:
    """Return the read model of one stored board.

    The board is reported as offline because connectivity belongs to the live
    layer of the hardware, not to a table row.

    Args:
        row: Row to shape.

    Returns:
        BoardView: Board shaped for display.
    """
    return BoardView(
        id=EspDeviceId.parse(row.id),
        name=row.name,
        online=False,
        last_seen_at=None if row.last_seen_at is None else mappers.as_utc(row.last_seen_at),
        current_ssid=row.current_ssid,
    )


def claim_view_of(row: EspClaimRow) -> BoardClaimView:
    """Return the read model of one stored offer.

    The device key is never part of the answer: it is the credential of the board,
    and the only things a person needs are the code and the token of the offer.

    Args:
        row: Row to shape.

    Returns:
        BoardClaimView: Offer shaped for display.
    """
    return BoardClaimView(
        id=EspClaimId.parse(row.id),
        label=row.label,
        claim_token=row.claim_token,
        announced_at=mappers.as_utc(row.announced_at),
        expires_at=mappers.as_utc(row.expires_at),
    )
