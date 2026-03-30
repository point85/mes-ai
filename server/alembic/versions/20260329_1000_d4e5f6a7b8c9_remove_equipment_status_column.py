"""Remove equipment status column.

Equipment availability is now determined solely by state machine state
(PackML, SEMI E10, or user-defined). If no state machine is assigned,
100% availability is assumed.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-29 10:00:00.000000
"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("equipment", "status")


def downgrade() -> None:
    op.add_column(
        "equipment",
        op.Column("status", op.String(20), nullable=False, server_default="idle"),
    )
    # Remove the server_default after backfill
    op.alter_column("equipment", "status", server_default=None)
