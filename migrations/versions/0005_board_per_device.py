"""Плата, на которой стоит устройство, и единственность канала внутри платы.

До этой ревизии хранилище обещало один канал реле на аккаунт: один и тот же канал
нельзя было занять дважды. Из-за этого дом со второй платой был невозможен — две
платы, каждая со своим первым каналом, сталкивались. С этой ревизии устройство
помнит, на какой плате оно стоит, а правило канала считается внутри платы:
единственность держится на тройке (аккаунт, плата, канал), а аккаунт, устройства
которого плату не называют, остаётся под прежним правилом — поэтому строки, которые
уже лежат в таблице, не начинают конфликтовать друг с другом.

Revision ID: 0005_board_per_device
Revises: 0004_versions_and_channel
Created: 2026-02-02 00:00:00.000000

"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import context as migration_context
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
CHANNEL_LIMIT = 6


def upgrade() -> None:
    """Добавляет колонку платы и считает единственность канала внутри платы.

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
    """Возвращает единственность канала на аккаунт и убирает колонку платы.

    После этой ревизии у аккаунта с двумя платами могло появиться по устройству на
    одном и том же канале, а прежнее правило знает только аккаунт и такие строки
    отвергает. Поэтому перед ограничением каналы разводятся по свободным номерам
    аккаунта, а если номеров на всех не хватило, откат останавливается с объяснением:
    молча упасть на нарушении ограничения или молча удалить устройства — оба хуже
    отказа с причиной.

    Returns:
        None.

    Raises:
        RuntimeError: У аккаунта больше устройств, чем каналов у одной платы, и
            старую схему без удаления устройств не восстановить.
    """
    op.drop_index(PINNED_INDEX, table_name=DEVICES)
    op.drop_index(UNPINNED_INDEX, table_name=DEVICES)
    spread_channels()
    op.create_unique_constraint(LEGACY_CONSTRAINT, DEVICES, ["user_id", "channel"])
    op.drop_column(DEVICES, COLUMN_BOARD_ID)


def spread_channels() -> None:
    """Разводит устройства аккаунта по разным каналам.

    Порядок задан раскладкой строк, а не выбором: первое устройство аккаунта
    остаётся на своём канале, каждое следующее занимает наименьший свободный номер.
    Переназначение попадает в журнал, потому что после отката реле отвечает уже не
    тому устройству, которое человек туда поставил.

    Returns:
        None.

    Raises:
        RuntimeError: Свободных номеров у аккаунта больше нет.
    """
    if migration_context.is_offline_mode():
        return
    log = logging.getLogger(__name__)
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(f"SELECT id, user_id, channel FROM {DEVICES} ORDER BY user_id, id")
    ).fetchall()
    claimed: dict[object, set[int]] = {}
    for identifier, owner, channel in rows:
        used = claimed.setdefault(owner, set())
        if channel not in used:
            used.add(channel)
            continue
        free = next((number for number in range(1, CHANNEL_LIMIT + 1) if number not in used), None)
        if free is None:
            raise RuntimeError(
                f"{DEVICES}: account {owner} has more devices than one board can name; "
                "delete the devices of the extra boards before downgrading"
            )
        log.warning(
            "migration.channel_shifted table=%s user=%s device=%s was=%s now=%s",
            DEVICES,
            owner,
            identifier,
            channel,
            free,
        )
        bind.execute(
            sa.text(f"UPDATE {DEVICES} SET channel = :channel WHERE id = :id").bindparams(
                channel=free, id=identifier
            )
        )
        used.add(free)
