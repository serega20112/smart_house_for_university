"""Versions of the rows and the uniqueness of the relay channels.

Two writers of the same aggregate used to erase each other's change: everybody
wrote the row whole, and the loser of a race simply wrote second. From now on a
row remembers its revision, a writer says which revision it read, and a stale
writer touches nothing instead of overwriting a change it never saw.

Two devices of one account used to be able to claim the same relay channel,
because the check was a lookup a moment before the write. The store says the
rule now: one channel, one device per account, so no race can wire two devices
to the same contact.

Revision ID: 0004_versions_and_channel
Revises: 0003_board_networks
Created: 2026-02-01 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context as migration_context
from alembic import op

revision: str = "0004_versions_and_channel"
down_revision: str | None = "0003_board_networks"
branch_labels: str | None = None
depends_on: str | None = None

DEVICES = "devices"
SCENARIOS = "scenarios"
AUTOMATION = "automation"
COLUMN_VERSION = "version"
CONSTRAINT_NAME = "uq_devices_user_id_channel"
LEGACY_USER_INDEX = "ix_devices_user_id"
LEGACY_CHANNEL_INDEX = "ix_devices_channel"
CHANNEL_LIMIT = 32


def upgrade() -> None:
    """Add the version columns and the channel uniqueness.

    Returns:
        None.
    """
    version = sa.Column(COLUMN_VERSION, sa.Integer(), nullable=False, server_default="0")
    for table in (DEVICES, SCENARIOS, AUTOMATION):
        op.add_column(table, version.copy())
    # Two devices of an account may already sit on one channel, and the store
    # refuses that from now on: rewrite every passing device to the first free
    # channel instead of guessing which one is right.
    shift_duplicates(DEVICES, COLUMN_VERSION)
    op.create_unique_constraint(CONSTRAINT_NAME, DEVICES, ["user_id", "channel"])
    op.drop_index(LEGACY_USER_INDEX, table_name=DEVICES)
    op.drop_index(LEGACY_CHANNEL_INDEX, table_name=DEVICES)


def downgrade() -> None:
    """Remove the version columns and the channel uniqueness.

    Returns:
        None.
    """
    op.create_index(LEGACY_USER_INDEX, DEVICES, ["user_id"])
    op.create_index(LEGACY_CHANNEL_INDEX, DEVICES, ["channel"])
    op.drop_constraint(CONSTRAINT_NAME, DEVICES, type_="unique")
    for table in (DEVICES, SCENARIOS, AUTOMATION):
        op.drop_column(table, COLUMN_VERSION)


def shift_duplicates(table_name: str, column_name: str) -> None:
    """Give every duplicate channel of an account a free one.

    The rows keep the order they were stored in, so the rewrite is a naming
    convention rather than a decision: the first stored device keeps its relay
    and every other one takes the smallest number the account has left free.

    Args:
        table_name: Table the duplicates live in.
        column_name: Name of the version column, unused but kept for symmetry.

    Returns:
        None.
    """
    del column_name
    if migration_context.is_offline_mode():
        return
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(f"SELECT id, user_id, channel FROM {table_name} ORDER BY user_id, id")
    ).fetchall()
    claimed: dict[object, set[int]] = {}
    for identifier, owner, channel in rows:
        used = claimed.setdefault(owner, set())
        if channel not in used:
            used.add(channel)
            continue
        free = next(number for number in range(1, CHANNEL_LIMIT + 1) if number not in used)
        if free > CHANNEL_LIMIT:
            raise RuntimeError(f"{table_name}: account {owner} has more devices than channels")
        bind.execute(
            sa.text(f"UPDATE {table_name} SET channel = :channel WHERE id = :id").bindparams(
                channel=free, id=identifier
            )
        )
        used.add(free)
