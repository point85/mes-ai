"""redesign UoM: classes (scalar/quotient/product/power), 5 types, clean old data

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-11 00:01:00.000000

Changes:
  - Add uom_class VARCHAR(20) NOT NULL DEFAULT 'scalar'
  - Add exponent  INTEGER NULL
  - Rename FK columns numerator_uom_id → left_uom_id,
                       denominator_uom_id → right_uom_id
  - Migrate old 'rate' uom_type records to uom_class='quotient' with
    uom_type set from their left (numerator) component
  - Rename uom_type 'count' → 'other'
  - Delete records with uom_type NOT IN (mass, length, time, temperature, other)
    (handles: volume, rate, custom, and any orphaned records)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VALID_TYPES = ('mass', 'length', 'time', 'temperature', 'other')


def upgrade() -> None:
    # ── 1. Add new columns ───────────────────────────────────────────
    op.add_column(
        'units_of_measure',
        sa.Column('uom_class', sa.String(20), nullable=False, server_default='scalar',
                  comment='scalar | quotient | product | power'),
    )
    op.add_column(
        'units_of_measure',
        sa.Column('exponent', sa.Integer(), nullable=True,
                  comment='Integer exponent for power-class UoMs'),
    )

    # ── 2. Rename FK columns ─────────────────────────────────────────
    op.alter_column('units_of_measure', 'numerator_uom_id', new_column_name='left_uom_id')
    op.alter_column('units_of_measure', 'denominator_uom_id', new_column_name='right_uom_id')

    # ── 3. Set uom_class = 'quotient' for old rate-type records ──────
    #        and resolve their uom_type from the left (numerator) component.
    #        We use a subquery join for the type lookup.
    op.execute("""
        UPDATE units_of_measure AS u
        SET uom_class = 'quotient',
            uom_type  = COALESCE(
                (SELECT n.uom_type
                 FROM units_of_measure n
                 WHERE n.id = u.left_uom_id),
                u.uom_type
            )
        WHERE u.left_uom_id IS NOT NULL
          AND u.uom_class = 'scalar'
    """)

    # ── 4. Rename 'count' → 'other' ──────────────────────────────────
    op.execute("UPDATE units_of_measure SET uom_type = 'other' WHERE uom_type = 'count'")

    # ── 5. Null out nullable FK columns pointing to composite UoMs that will
    #        be reclassified (safety step before touching composite records).
    #        No deletes — dependent tables may hold NOT NULL references.
    #        For composite records referencing unsupported scalar types, just
    #        update their uom_type to 'other' so they remain valid.
    op.execute("""
        UPDATE units_of_measure AS parent
        SET uom_type = 'other'
        WHERE uom_class != 'scalar'
          AND (
              left_uom_id IN (
                  SELECT id FROM units_of_measure
                  WHERE uom_type NOT IN ('mass', 'length', 'time', 'temperature', 'other')
              )
              OR right_uom_id IN (
                  SELECT id FROM units_of_measure
                  WHERE uom_type NOT IN ('mass', 'length', 'time', 'temperature', 'other')
              )
          )
    """)

    # ── 6. Convert remaining unsupported scalar types to 'other' ─────────────
    #        Deleting is unsafe: other tables (bom_items, material_definitions,
    #        equipment_materials, etc.) may hold NOT NULL FK references.
    #        Reclassifying to 'other' keeps referential integrity intact.
    op.execute("""
        UPDATE units_of_measure
        SET uom_type = 'other'
        WHERE uom_type NOT IN ('mass', 'length', 'time', 'temperature', 'other')
    """)


def downgrade() -> None:
    # Rename columns back
    op.alter_column('units_of_measure', 'left_uom_id', new_column_name='numerator_uom_id')
    op.alter_column('units_of_measure', 'right_uom_id', new_column_name='denominator_uom_id')
    op.drop_column('units_of_measure', 'exponent')
    op.drop_column('units_of_measure', 'uom_class')
