"""Add mole (mol) and candela (cd) SI base unit UoMs.

Introduces two new uom_type values:
  - amount_of_substance  → mol (mole)
  - luminous_intensity   → cd  (candela)

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None

_UOMS: list[tuple[str, str, str, float]] = [
    ("mol", "mole",    "amount_of_substance", 1.0),
    ("cd",  "candela", "luminous_intensity",  1.0),
]


def upgrade() -> None:
    conn = op.get_bind()
    for symbol, name, uom_type, multiplier in _UOMS:
        conn.execute(
            text("""
                INSERT INTO units_of_measure
                    (id, symbol, name, uom_type, uom_class, multiplier, "offset",
                     is_builtin, is_active, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :symbol, :name, :uom_type, 'scalar',
                     :multiplier, 0.0, TRUE, TRUE, NOW(), NOW())
                ON CONFLICT (symbol) DO NOTHING
            """).bindparams(
                symbol=symbol,
                name=name,
                uom_type=uom_type,
                multiplier=multiplier,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    for symbol, *_ in _UOMS:
        conn.execute(
            text("DELETE FROM units_of_measure WHERE symbol = :s").bindparams(s=symbol)
        )
