"""Ревизии строк и единственность канала реле.

Два писателя одного агрегата стирали изменение друг друга: каждый писал строку
целиком, и проигравший гонку просто писал вторым. Теперь строка помнит свою
ревизию, писатель говорит, какую ревизию он прочитал, а устаревший писатель ничего
не трогает вместо того, чтобы перетереть изменение, которого не видел.

Два устройства одного аккаунта раньше могли занять один канал реле, потому что
проверка была чтением за мгновение до записи. Теперь правило говорит хранилище:
один канал — одно устройство на аккаунт, и никакая гонка не посадит два устройства
на один контакт.

Revision ID: 0004_versions_and_channel
Revises: 0003_board_networks
Created: 2026-02-01 00:00:00.000000

"""

from __future__ import annotations

import logging

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
CHANNEL_LIMIT = 6


def upgrade() -> None:
    """Добавляет колонки ревизий и единственность канала.

    Два устройства аккаунта могли уже стоять на одном канале, а хранилище с этого
    момента такое отвергает: поэтому проходящее устройство переезжает на первый
    свободный канал, а не выбирается, кто из двух прав.

    Returns:
        None.
    """
    version = sa.Column(COLUMN_VERSION, sa.Integer(), nullable=False, server_default="0")
    for table in (DEVICES, SCENARIOS, AUTOMATION):
        op.add_column(table, version.copy())
    shift_duplicates(DEVICES)
    op.create_unique_constraint(CONSTRAINT_NAME, DEVICES, ["user_id", "channel"])
    op.drop_index(LEGACY_USER_INDEX, table_name=DEVICES)
    op.drop_index(LEGACY_CHANNEL_INDEX, table_name=DEVICES)


def downgrade() -> None:
    """Убирает колонки ревизий и единственность канала.

    Returns:
        None.
    """
    op.create_index(LEGACY_USER_INDEX, DEVICES, ["user_id"])
    op.create_index(LEGACY_CHANNEL_INDEX, DEVICES, ["channel"])
    op.drop_constraint(CONSTRAINT_NAME, DEVICES, type_="unique")
    for table in (DEVICES, SCENARIOS, AUTOMATION):
        op.drop_column(table, COLUMN_VERSION)


def shift_duplicates(table_name: str) -> None:
    """Переносит повторяющиеся каналы аккаунта на свободные.

    Строки перебираются в том порядке, в котором легли в таблицу, поэтому переезд —
    это договорённость об именах, а не решение: первое сохранённое устройство
    остаётся на своём реле, а каждое следующее занимает наименьший номер, который у
    аккаунта ещё свободен.

    Каждый переезд попадает в журнал: без записи никто не узнает, что реле, которое
    человек считал своим, теперь щёлкает другое устройство, — а ревизия, о которой
    нельзя рассказать, это тихая потеря данных.

    Args:
        table_name: Таблица, в которой ищутся повторяющиеся каналы.

    Returns:
        None.
    """
    if migration_context.is_offline_mode():
        return
    log = logging.getLogger(__name__)
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
        free = next((number for number in range(1, CHANNEL_LIMIT + 1) if number not in used), None)
        if free is None:
            raise RuntimeError(f"{table_name}: account {owner} has more devices than channels")
        log.warning(
            "migration.channel_shifted table=%s user=%s device=%s was=%s now=%s",
            table_name,
            owner,
            identifier,
            channel,
            free,
        )
        bind.execute(
            sa.text(f"UPDATE {table_name} SET channel = :channel WHERE id = :id").bindparams(
                channel=free, id=identifier
            )
        )
        used.add(free)
