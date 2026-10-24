"""Board a device sits on, and channel uniqueness per board.

Until now the store promised one relay channel per account: the same channel could not
be claimed twice. That made a home with a second board impossible — two boards each
running channel one would collide. From this revision a device also remembers which
board it belongs to, and the channel rule is scoped to that board: uniqueness holds per
(board, channel), while an account whose devices name no board keeps the old per-account
rule untouched, so existing rows never start conflicting.

Revision ID: 0005_board_per_device
Revises: 0004_versions_and_channel
Created: 2026-02-02 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005_board_per_device"
down_revision: str | None = "0004_versions_and_channel"
branch_labels: str | None = None
depends_on: str | None = None

DEVICES = "devices"
ESP_DEVICES = "esp_devices"
COLUMN_BOARD_ID = "board_id"
LEGACY_CONSTRAINT = "uq_devices_user_id_channel"
UNPINNED_INDEX = "uq_devices_user_id_channel"
PINNED_INDEX = "uq_devices_board_id_channel"


def upgrade() -> None:
    """Add the board column and scope channel uniqueness to a board.

    Returns:
        None.
    """
    op.add_column(
        DEVICES,
        sa.Column(
            COLUMN_BOARD_ID,
            sa.Uuid(),
            sa.ForeignKey(f"{ESP_DEVICES}.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.drop_constraint(LEGACY_CONSTRAINT, DEVICES, type_="unique")
    op.create_index(
        UNPINNED_INDEX,
        DEVICES,
        ["user_id", "channel"],
        unique=True,
        postgresql_where=sa.text("board_id IS NULL"),
    )
    op.create_index(
        PINNED_INDEX,
        DEVICES,
        ["user_id", COLUMN_BOARD_ID, "channel"],
        unique=True,
        postgresql_where=sa.text("board_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Restore the per-account channel constraint and drop the board column.

    Returns:
        None.
    """
    op.drop_index(PINNED_INDEX, table_name=DEVICES)
    op.drop_index(UNPINNED_INDEX, table_name=DEVICES)
    op.create_unique_constraint(LEGACY_CONSTRAINT, DEVICES, ["user_id", "channel"])
    op.drop_column(DEVICES, COLUMN_BOARD_ID)
