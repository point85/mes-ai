"""add persisted dashboard alert rules

Revision ID: 20261103_0001
Revises: 20260907_0001
Create Date: 2026-11-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261103_0001"
down_revision = "20260907_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_alert_rules",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("metric", sa.String(length=40), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dashboard_alert_rules_equipment_id",
        "dashboard_alert_rules",
        ["equipment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dashboard_alert_rules_equipment_id", table_name="dashboard_alert_rules")
    op.drop_table("dashboard_alert_rules")
