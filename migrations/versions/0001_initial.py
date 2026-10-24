"""Начальная схема бэкенда умного дома.

Все таблицы слоя хранения создаются здесь и больше нигде: ничто в приложении не
имеет права завести таблицу, поэтому развёртывание всегда может собрать схему с
нуля, а ревью читает схему как diff.

Коллекции, которые раньше лежали непрозрачными сгустками, стали настоящими
таблицами с настоящими внешними ключами: именно поэтому хранилище держит аккаунты
порознь, защищает порядок раскладки и уносит удаление в строки, описывавшие то,
чего больше нет.

Revision ID: 0001_initial
Revises:
Created: 2026-01-01 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Создаёт каждую таблицу схемы.

    Returns:
        None.
    """
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("automation_enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_devices_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_devices"),
    )
    op.create_index(op.f("ix_devices_user_id"), "devices", ["user_id"])
    op.create_index(op.f("ix_devices_channel"), "devices", ["channel"])

    op.create_table(
        "device_capabilities",
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("capability", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_device_capabilities_device_id_devices",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("device_id", "capability", name="pk_device_capabilities"),
    )

    op.create_table(
        "automation",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("target_temperature", sa.Float(), nullable=False),
        sa.Column("temperature_tolerance", sa.Float(), nullable=False),
        sa.Column("target_humidity", sa.Float(), nullable=False),
        sa.Column("humidity_tolerance", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_automation_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_automation"),
    )

    op.create_table(
        "automation_participants",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_automation_participants_device_id_devices",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_automation_participants_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "device_id", name="pk_automation_participants"),
    )

    op.create_table(
        "preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("temperature_unit", sa.String(length=2), nullable=False),
        sa.Column("theme", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("show_command_chat", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_preferences"),
    )

    op.create_table(
        "dashboard",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_dashboard_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_dashboard"),
    )

    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=60), nullable=True),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_dashboard_widgets_device_id_devices",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_dashboard_widgets_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dashboard_widgets"),
    )
    op.create_index(op.f("ix_dashboard_widgets_user_id"), "dashboard_widgets", ["user_id"])

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("target", sa.String(length=120), nullable=True),
        sa.Column("completion_behavior", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_scenarios_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scenarios"),
    )
    op.create_index(op.f("ix_scenarios_user_id"), "scenarios", ["user_id"])
    op.create_index(op.f("ix_scenarios_status"), "scenarios", ["status"])
    op.create_index(op.f("ix_scenarios_user_id_created_at"), "scenarios", ["user_id", "created_at"])

    op.create_table(
        "scenario_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=16), nullable=False),
        sa.Column("target_temperature", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name="fk_scenario_actions_scenario_id_scenarios",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scenario_actions"),
    )
    op.create_index(op.f("ix_scenario_actions_scenario_id"), "scenario_actions", ["scenario_id"])

    op.create_table(
        "scenario_captured_statuses",
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_scenario_captured_statuses_device_id_devices",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name="fk_scenario_captured_statuses_scenario_id_scenarios",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scenario_id", "device_id", name="pk_scenario_captured_statuses"),
    )

    op.create_table(
        "esp_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("pairing_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_esp_devices_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_esp_devices"),
        sa.UniqueConstraint("pairing_key", name="uq_esp_devices_pairing_key"),
    )
    op.create_index(op.f("ix_esp_devices_user_id"), "esp_devices", ["user_id"])

    op.create_table(
        "esp_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=8), nullable=False),
        sa.Column("claim_token", sa.String(length=16), nullable=False),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["claimed_by"],
            ["users.id"],
            name="fk_esp_claims_claimed_by_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_esp_claims"),
        sa.UniqueConstraint("claim_token", name="uq_esp_claims_claim_token"),
    )
    op.create_index(op.f("ix_esp_claims_device_key"), "esp_claims", ["device_key"])
    op.create_index(op.f("ix_esp_claims_label"), "esp_claims", ["label"])
    op.create_index(op.f("ix_esp_claims_expires_at"), "esp_claims", ["expires_at"])


def downgrade() -> None:
    """Удаляет каждую таблицу схемы.

    Returns:
        None.
    """
    op.drop_index(op.f("ix_esp_claims_expires_at"), table_name="esp_claims")
    op.drop_index(op.f("ix_esp_claims_label"), table_name="esp_claims")
    op.drop_index(op.f("ix_esp_claims_device_key"), table_name="esp_claims")
    op.drop_table("esp_claims")

    op.drop_index(op.f("ix_esp_devices_user_id"), table_name="esp_devices")
    op.drop_table("esp_devices")

    op.drop_table("scenario_captured_statuses")

    op.drop_index(op.f("ix_scenario_actions_scenario_id"), table_name="scenario_actions")
    op.drop_table("scenario_actions")

    op.drop_index(op.f("ix_scenarios_user_id_created_at"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_status"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_user_id"), table_name="scenarios")
    op.drop_table("scenarios")

    op.drop_index(op.f("ix_dashboard_widgets_user_id"), table_name="dashboard_widgets")
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboard")

    op.drop_table("preferences")
    op.drop_table("automation_participants")
    op.drop_table("automation")

    op.drop_table("device_capabilities")

    op.drop_index(op.f("ix_devices_channel"), table_name="devices")
    op.drop_index(op.f("ix_devices_user_id"), table_name="devices")
    op.drop_table("devices")

    op.drop_table("users")
