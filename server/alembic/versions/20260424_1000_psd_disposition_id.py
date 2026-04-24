"""process_segment_dependencies: add disposition_id FK

Adds an optional ``disposition_id`` FK on
``process_segment_dependencies`` so a disposition-conditioned transition
can reference a catalog ``Disposition`` row instead of carrying only a
free-text label. Enables per-segment dispositions wired to the catalog
for dispatcher selection.

Revision ID: d8a5f0e9c31b
Revises: b2c9e0117f31
Create Date: 2026-04-24 10:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8a5f0e9c31b"
down_revision: Union[str, None] = "b2c9e0117f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "process_segment_dependencies",
        sa.Column("disposition_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "process_segment_dependencies_disposition_id_fkey",
        "process_segment_dependencies", "dispositions",
        ["disposition_id"], ["id"],
    )
    op.create_index(
        "ix_process_segment_dependencies_disposition_id",
        "process_segment_dependencies",
        ["disposition_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_process_segment_dependencies_disposition_id",
        table_name="process_segment_dependencies",
    )
    op.drop_constraint(
        "process_segment_dependencies_disposition_id_fkey",
        "process_segment_dependencies",
        type_="foreignkey",
    )
    op.drop_column("process_segment_dependencies", "disposition_id")
