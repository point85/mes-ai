"""Restore UoMs needed for CPG and Electronics demo seed data.

Re-adds the units deleted in migrations 0004 and 0006:
  - °Bx  (degrees Brix)
  - pH
  - CFU/mL (colony-forming units per mL)
  - N    (newton)
  - A    (ampere)
  - mA   (milliampere)
  - V    (volt)
  - Pa   (pascal)
  - kPa  (kilopascal)
  - Nm   (newton-meter)
  - count

Also ensures other UoMs required by the demo step parameters and data
definitions exist (idempotent via ON CONFLICT DO NOTHING):
  - µm         (micrometer — length)
  - cph        (components per hour)
  - mm/min     (millimeters per minute — scalar for migration; seed creates it
                as a proper quotient on fresh installs)
  - RPM        (revolutions per minute)
  - bottle/min
  - label/min

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Each entry: (symbol, name, uom_type, uom_class, multiplier, offset, is_builtin)
# ---------------------------------------------------------------------------
_UOMS: list[tuple[str, str, str, str, float, float, bool]] = [
    # Electrical
    ("A",           "ampere",                      "electrical",  "scalar", 1.0,        0.0, True),
    ("mA",          "milliampere",                 "electrical",  "scalar", 0.001,      0.0, True),
    ("V",           "volt",                        "electrical",  "scalar", 1.0,        0.0, True),
    # Force / pressure / torque
    ("N",           "newton",                      "force",  "scalar", 1.0,        0.0, True),
    ("Pa",          "pascal",                      "force",  "scalar", 1.0,        0.0, True),
    ("kPa",         "kilopascal",                  "force",  "scalar", 1000.0,     0.0, True),
    ("Nm",          "newton-meter",                "force",  "scalar", 1.0,        0.0, True),
    # Process / biological
    ("\u00b0Bx",    "degrees Brix",                "mass",  "scalar", 1.0,        0.0, True),
    ("pH",          "pH",                          "other",  "scalar", 1.0,        0.0, True),
    ("CFU/mL",      "colony-forming units per mL", "other",  "scalar", 1.0,        0.0, True),
    # Discrete / rates
    ("count",       "count",                       "other",  "scalar", 1.0,        0.0, True),
    ("cph",         "components per hour",         "other",  "scalar", 1.0,        0.0, False),
    ("RPM",         "revolutions per minute",      "other",  "scalar", 1.0/60.0,   0.0, False),
    ("bottle/min",  "bottles per minute",          "other",  "scalar", 1.0,        0.0, False),
    ("label/min",   "labels per minute",           "other",  "scalar", 1.0,        0.0, False),
    # Length (fine scale)
    ("\u00b5m",     "micrometer",                  "length", "scalar", 1.0e-6,     0.0, True),
    # Compound speed (scalar approximation; proper quotient built by seed on fresh install)
    ("mm/min",      "millimeters per minute",      "length", "scalar", 1.0/60000,  0.0, False),
]


def upgrade() -> None:
    conn = op.get_bind()
    for symbol, name, uom_type, uom_class, multiplier, offset, is_builtin in _UOMS:
        conn.execute(text("""
            INSERT INTO units_of_measure
                (id, symbol, name, uom_type, uom_class, multiplier, "offset",
                 is_builtin, is_active, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :symbol, :name, :uom_type, :uom_class,
                 :multiplier, :offset, :is_builtin, TRUE,
                 NOW(), NOW())
            ON CONFLICT (symbol) DO NOTHING
        """).bindparams(
            symbol=symbol,
            name=name,
            uom_type=uom_type,
            uom_class=uom_class,
            multiplier=multiplier,
            offset=offset,
            is_builtin=is_builtin,
        ))


def downgrade() -> None:
    # Only remove what this migration added; leave any rows that pre-existed.
    conn = op.get_bind()
    symbols = [row[0] for row in _UOMS]
    for symbol in symbols:
        conn.execute(
            text("DELETE FROM units_of_measure WHERE symbol = :s AND is_builtin = FALSE OR symbol = :s AND is_builtin = TRUE")
            .bindparams(s=symbol)
        )
