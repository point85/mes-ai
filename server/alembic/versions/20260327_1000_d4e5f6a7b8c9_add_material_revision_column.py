"""Add revision column to material_definitions

Stores material revision level from ERPs that support it
(e.g. Oracle RevisionCode). Nullable — SAP materials have no revision.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "material_definitions",
        sa.Column(
            "revision",
            sa.String(20),
            nullable=True,
            comment="Material revision level (e.g. Oracle RevisionCode). Null if ERP has no revisions.",
        ),
    )


def downgrade() -> None:
    op.drop_column("material_definitions", "revision")
