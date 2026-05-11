"""Delete 'count' UoM from other type.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Null out nullable FK references first
    _subq = (
        "SELECT id FROM units_of_measure"
        " WHERE uom_type = 'other' AND (symbol = 'count' OR name ILIKE 'count')"
    )
    for table, col in (
        ("equipment_class_properties", "uom_id"),
        ("data_definitions", "uom_id"),
        ("segment_parameters", "uom_id"),
    ):
        conn.execute(text(f"UPDATE {table} SET {col} = NULL WHERE {col} IN ({_subq})"))

    conn.execute(
        text(
            "DELETE FROM units_of_measure"
            " WHERE uom_type = 'other' AND (symbol = 'count' OR name ILIKE 'count')"
        )
    )


def downgrade() -> None:
    pass
