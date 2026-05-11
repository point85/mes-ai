"""Delete fluid ounce (fl oz) UoM.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    _subq = "SELECT id FROM units_of_measure WHERE symbol = 'fl oz'"
    for table, col in (
        ("equipment_class_properties", "uom_id"),
        ("data_definitions", "uom_id"),
        ("segment_parameters", "uom_id"),
    ):
        conn.execute(text(f"UPDATE {table} SET {col} = NULL WHERE {col} IN ({_subq})"))
    conn.execute(text("DELETE FROM units_of_measure WHERE symbol = 'fl oz'"))


def downgrade() -> None:
    pass
