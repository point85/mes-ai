"""Delete duplicate fluid ounce with underscore symbol (fl_oz).

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    _subq = "SELECT id FROM units_of_measure WHERE symbol = 'fl_oz'"
    for table, col in (
        ("equipment_class_properties", "uom_id"),
        ("data_definitions", "uom_id"),
        ("segment_parameters", "uom_id"),
    ):
        conn.execute(text(f"UPDATE {table} SET {col} = NULL WHERE {col} IN ({_subq})"))
    conn.execute(text("DELETE FROM units_of_measure WHERE symbol = 'fl_oz'"))


def downgrade() -> None:
    pass
