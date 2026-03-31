"""Add reasons table for hierarchical loss/downtime codes.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-30 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reasons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(4), unique=True, nullable=False, index=True,
                   comment="4-character reason code, e.g. '1000'"),
        sa.Column("name", sa.String(255), nullable=False,
                   comment="Short descriptive name"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("oee_bucket", sa.String(30), nullable=False,
                   comment="OEE loss bucket: downtime_planned, downtime_unplanned, etc."),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("reasons.id"),
                   nullable=True, index=True,
                   comment="Parent reason for hierarchical grouping (null = top-level)"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reasons")
