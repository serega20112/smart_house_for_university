"""Network of every board.

A board keeps the network of its own in its flash, and this table is the copy the
server works with: the interface shows it, and the board is asked for it again
when it comes back after a change it could not apply.

The password of the network is stored here because it has to reach the board one
more time in that case, and it never leaves the server in an answer. A row
belongs to one board and disappears with it.

The network a board reports being on is kept next to the board itself: it is
what the board said about itself the last time it was seen, exactly like the
moment of that handshake.

Revision ID: 0003_board_networks
Revises: 0002_reference_phrases
Created: 2026-01-03 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0003_board_networks"
down_revision: str | None = "0002_reference_phrases"
branch_labels: str | None = None
depends_on: str | None = None

TABLE_NAME = "board_networks"
COLUMN_BOARD_ID = "board_id"
COLUMN_USER_ID = "user_id"
COLUMN_SSID = "ssid"
COLUMN_PASSWORD = "password"
COLUMN_HOST = "host"
COLUMN_SERVER_PORT = "server_port"
COLUMN_SOCKET_PORT = "socket_port"
COLUMN_SOCKET_PATH = "socket_path"
COLUMN_UPDATED_AT = "updated_at"
SSID_WIDTH = 32
PASSWORD_WIDTH = 64
HOST_WIDTH = 64
PATH_WIDTH = 64
PRIMARY_KEY = "pk_board_networks"
FOREIGN_KEY_BOARD = "fk_board_networks_board_id_esp_devices"
FOREIGN_KEY_USER = "fk_board_networks_user_id_users"
COLUMN_CURRENT_SSID = "current_ssid"
TABLE_BOARDS = "esp_devices"


def upgrade() -> None:
    """Create the table of the network of every board.

    Returns:
        None.
    """
    op.add_column(
        TABLE_BOARDS,
        sa.Column(COLUMN_CURRENT_SSID, sa.String(length=SSID_WIDTH), nullable=True),
    )
    op.create_table(
        TABLE_NAME,
        sa.Column(COLUMN_BOARD_ID, sa.Uuid(), nullable=False),
        sa.Column(COLUMN_USER_ID, sa.Uuid(), nullable=False),
        sa.Column(COLUMN_SSID, sa.String(length=SSID_WIDTH), nullable=False),
        sa.Column(COLUMN_PASSWORD, sa.String(length=PASSWORD_WIDTH), nullable=False),
        sa.Column(COLUMN_HOST, sa.String(length=HOST_WIDTH), nullable=False),
        sa.Column(COLUMN_SERVER_PORT, sa.Integer(), nullable=False),
        sa.Column(COLUMN_SOCKET_PORT, sa.Integer(), nullable=False),
        sa.Column(COLUMN_SOCKET_PATH, sa.String(length=PATH_WIDTH), nullable=False),
        sa.Column(COLUMN_UPDATED_AT, sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            [COLUMN_BOARD_ID],
            ["esp_devices.id"],
            name=FOREIGN_KEY_BOARD,
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            [COLUMN_USER_ID],
            ["users.id"],
            name=FOREIGN_KEY_USER,
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(COLUMN_BOARD_ID, name=PRIMARY_KEY),
    )
    op.create_index(op.f("ix_board_networks_user_id"), TABLE_NAME, [COLUMN_USER_ID])


def downgrade() -> None:
    """Remove the table of the network of every board.

    Returns:
        None.
    """
    op.drop_index(op.f("ix_board_networks_user_id"), table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
    op.drop_column(TABLE_BOARDS, COLUMN_CURRENT_SSID)
