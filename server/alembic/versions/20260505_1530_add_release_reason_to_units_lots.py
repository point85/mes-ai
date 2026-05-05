"""add_release_reason_to_units_lots

Add release_reason column to units and lots tables to record the
disposition/reason selected when releasing a unit or lot from hold.
Add 'release' as a valid disposition category.

Revision ID: aa11bb22cc33
Revises: 9a8b7c6d5e4f
Create Date: 2026-05-05 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aa11bb22cc33'
down_revision: Union[str, None] = '9a8b7c6d5e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "units",
        sa.Column(
            "release_reason",
            sa.Text(),
            nullable=True,
            comment="Disposition/reason selected when releasing the unit from hold",
        ),
    )
    op.add_column(
        "lots",
        sa.Column(
            "release_reason",
            sa.Text(),
            nullable=True,
            comment="Disposition/reason selected when releasing the lot from hold",
        ),
    )


def downgrade() -> None:
    op.drop_column("units", "release_reason")
    op.drop_column("lots", "release_reason")
