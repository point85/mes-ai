"""RCA: add defect_codes catalog and scrap/failure columns to WIP tables

Implements root-cause analysis (RCA) data foundation:
  A. scrap_reason, scrap_disposition, defect_code_id, scrapped_at, hold_reason
     on units and lots — persists scrap context that was previously event-only.
  B. disposition, failure_mode, defect_code_id, scrap_reason, result
     on segment_response_units and segment_response_lots — per-step RCA columns.
  D. defect_codes catalog table for structured Pareto analysis.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── D: defect_codes catalog ─────────────────────────────────────
    op.create_table(
        "defect_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_defect_codes_code", "defect_codes", ["code"], unique=True)
    op.create_index("ix_defect_codes_category", "defect_codes", ["category"])

    # ── A: scrap / hold columns on units ───────────────────────────
    op.add_column("units", sa.Column("scrap_reason", sa.Text(), nullable=True))
    op.add_column("units", sa.Column("scrap_disposition", sa.String(50), nullable=True))
    op.add_column("units", sa.Column("defect_code_id", sa.Uuid(), nullable=True))
    op.add_column("units", sa.Column("scrapped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("units", sa.Column("hold_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_units_defect_code_id",
        "units", "defect_codes",
        ["defect_code_id"], ["id"],
    )
    op.create_index("ix_units_defect_code_id", "units", ["defect_code_id"])

    # ── A: scrap / hold columns on lots ────────────────────────────
    op.add_column("lots", sa.Column("scrap_reason", sa.Text(), nullable=True))
    op.add_column("lots", sa.Column("scrap_disposition", sa.String(50), nullable=True))
    op.add_column("lots", sa.Column("defect_code_id", sa.Uuid(), nullable=True))
    op.add_column("lots", sa.Column("scrapped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lots", sa.Column("hold_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_lots_defect_code_id",
        "lots", "defect_codes",
        ["defect_code_id"], ["id"],
    )
    op.create_index("ix_lots_defect_code_id", "lots", ["defect_code_id"])

    # ── B: per-step RCA columns on segment_response_units ──────────
    op.add_column("segment_response_units", sa.Column("disposition", sa.String(100), nullable=True))
    op.add_column("segment_response_units", sa.Column("failure_mode", sa.String(200), nullable=True))
    op.add_column("segment_response_units", sa.Column("defect_code_id", sa.Uuid(), nullable=True))
    op.add_column("segment_response_units", sa.Column("scrap_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_sru_defect_code_id",
        "segment_response_units", "defect_codes",
        ["defect_code_id"], ["id"],
    )
    op.create_index("ix_sru_defect_code_id", "segment_response_units", ["defect_code_id"])

    # ── B: per-step RCA columns on segment_response_lots ───────────
    op.add_column("segment_response_lots", sa.Column("result", sa.String(20), nullable=True))
    op.add_column("segment_response_lots", sa.Column("disposition", sa.String(100), nullable=True))
    op.add_column("segment_response_lots", sa.Column("failure_mode", sa.String(200), nullable=True))
    op.add_column("segment_response_lots", sa.Column("defect_code_id", sa.Uuid(), nullable=True))
    op.add_column("segment_response_lots", sa.Column("scrap_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_srl_defect_code_id",
        "segment_response_lots", "defect_codes",
        ["defect_code_id"], ["id"],
    )
    op.create_index("ix_srl_defect_code_id", "segment_response_lots", ["defect_code_id"])


def downgrade() -> None:
    # segment_response_lots
    op.drop_index("ix_srl_defect_code_id", table_name="segment_response_lots")
    op.drop_constraint("fk_srl_defect_code_id", "segment_response_lots", type_="foreignkey")
    for col in ("scrap_reason", "defect_code_id", "failure_mode", "disposition", "result"):
        op.drop_column("segment_response_lots", col)

    # segment_response_units
    op.drop_index("ix_sru_defect_code_id", table_name="segment_response_units")
    op.drop_constraint("fk_sru_defect_code_id", "segment_response_units", type_="foreignkey")
    for col in ("scrap_reason", "defect_code_id", "failure_mode", "disposition"):
        op.drop_column("segment_response_units", col)

    # lots
    op.drop_index("ix_lots_defect_code_id", table_name="lots")
    op.drop_constraint("fk_lots_defect_code_id", "lots", type_="foreignkey")
    for col in ("hold_reason", "scrapped_at", "defect_code_id", "scrap_disposition", "scrap_reason"):
        op.drop_column("lots", col)

    # units
    op.drop_index("ix_units_defect_code_id", table_name="units")
    op.drop_constraint("fk_units_defect_code_id", "units", type_="foreignkey")
    for col in ("hold_reason", "scrapped_at", "defect_code_id", "scrap_disposition", "scrap_reason"):
        op.drop_column("units", col)

    # defect_codes
    op.drop_index("ix_defect_codes_category", table_name="defect_codes")
    op.drop_index("ix_defect_codes_code", table_name="defect_codes")
    op.drop_table("defect_codes")
