"""add plugin_config table

Stores per-plugin enabled/disabled state and user-overridden configuration
values for the plugin management framework.

Revision ID: a1b2c3d4e5f6
Revises: c6b762b32512
Create Date: 2026-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c6b762b32512"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plugin_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "plugin_id",
            sa.String(255),
            nullable=False,
            unique=True,
            index=True,
            comment="Plugin identifier matching manifest.id",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether the plugin should be started on boot",
        ),
        sa.Column(
            "config_overrides",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="User-overridden config values (merged over manifest defaults)",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Optional admin notes about the plugin configuration",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft delete flag",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("plugin_config")
