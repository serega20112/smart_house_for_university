"""Плата и её владелец связаны составным ключом, разрыв — только явный.

До этой ревизии удаление платы каскадно уносило все устройства, стоявшие на её
каналах, вместе со способностями, участием в автоматизации и карточками панели.
Теперь ссылка составная: устройство ссылается не просто на плату, а на пару
«плата и её владелец», поэтому чужая плата в поле `board_id` невозможна на уровне
хранилища. Удаление платы, за которой стоят устройства, запрещено, а не выполнено
молча.

Revision ID: 0006_board_detach_restrict
Revises: 0005_board_per_device
Created: 2026-10-24 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0006_board_detach_restrict"
down_revision: str | None = "0005_board_per_device"
branch_labels: str | None = None
depends_on: str | None = None

DEVICES = "devices"
ESP_DEVICES = "esp_devices"
BOARD_OWNER_CONSTRAINT = "fk_devices_board_owner"
BOARD_UNIQUE = "uq_esp_devices_id_user_id"
LEGACY_BOARD_FK = "devices_board_id_fkey"


def upgrade() -> None:
    """Переводит ссылку устройства на плату в составную и запрещает каскад."""
    op.create_unique_constraint(BOARD_UNIQUE, ESP_DEVICES, ["id", "user_id"])
    op.drop_constraint(LEGACY_BOARD_FK, DEVICES, type_="foreignkey")
    op.create_foreign_key(
        BOARD_OWNER_CONSTRAINT,
        DEVICES,
        ESP_DEVICES,
        ["board_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Возвращает одиночную ссылку с каскадом.

    Ревизия объявлена обратимой только для пустой таблицы устройств: после
    апгрейда у аккаунта могли появиться две платы с одинаковыми каналами, и
    восстановление ограничения «канал на аккаунт» упадёт на дубликатах. Поэтому
    строки, мешающие откату, снимаются вместе с привязкой к плате.
    """
    op.execute(
        sa.text(
            "DELETE FROM devices AS extra "
            "USING devices AS kept "
            "WHERE extra.user_id = kept.user_id "
            "AND extra.channel = kept.channel "
            "AND extra.id > kept.id"
        )
    )
    op.drop_constraint(BOARD_OWNER_CONSTRAINT, DEVICES, type_="foreignkey")
    op.create_foreign_key(
        LEGACY_BOARD_FK,
        DEVICES,
        ESP_DEVICES,
        ["board_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(BOARD_UNIQUE, ESP_DEVICES, type_="unique")
