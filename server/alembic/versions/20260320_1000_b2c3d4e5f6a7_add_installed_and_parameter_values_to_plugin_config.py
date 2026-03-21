"""add installed and parameter_values to plugin_config

Adds two columns to the plugin_config table to support the plugin
install lifecycle:
  - installed (bool): whether the plugin has been installed with parameters
  - parameter_values (JSONB): user-provided values for manifest-declared params

Also changes the enabled column default from true to false (plugins must
be explicitly enabled after installation).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'installed' column (default false)
    op.add_column(
        "plugin_config",
        sa.Column(
            "installed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether the plugin has been installed (parameters provided)",
        ),
    )

    # Add 'parameter_values' JSONB column (default empty object)
    op.add_column(
        "plugin_config",
        sa.Column(
            "parameter_values",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="User-provided parameter values (filled during install)",
        ),
    )

    # Change enabled default from true to false
    op.alter_column(
        "plugin_config",
        "enabled",
        server_default=sa.text("false"),
    )

    # Mark any existing rows as installed + enabled (backwards compat)
    op.execute("UPDATE plugin_config SET installed = true WHERE enabled = true")


def downgrade() -> None:
    # Revert enabled default back to true
    op.alter_column(
        "plugin_config",
        "enabled",
        server_default=sa.text("true"),
    )

    op.drop_column("plugin_config", "parameter_values")
    op.drop_column("plugin_config", "installed")
