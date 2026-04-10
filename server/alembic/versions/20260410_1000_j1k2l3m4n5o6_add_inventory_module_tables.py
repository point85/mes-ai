"""add inventory module tables

Revision ID: j1k2l3m4n5o6
Revises: ee4a56a35d22
Create Date: 2026-04-10 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "j1k2l3m4n5o6"
down_revision = "ee4a56a35d22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── storage_locations ────────────────────────────────────────────
    op.create_table(
        "storage_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "location_type", sa.String(20), nullable=False,
            server_default="storage",
            comment="Location type: receiving, storage, rip, staging, shipping",
        ),
        sa.Column("aisle", sa.String(20), nullable=True, comment="Aisle identifier (for storage locations)"),
        sa.Column("bay", sa.String(20), nullable=True, comment="Bay identifier within the aisle"),
        sa.Column("tier", sa.String(20), nullable=True, comment="Tier/shelf level within the bay"),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Site this location belongs to"),
        sa.Column("capacity", sa.Float(), nullable=True, comment="Maximum storage capacity"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_storage_locations_name", "storage_locations", ["name"])
    op.create_index("ix_storage_locations_code", "storage_locations", ["code"])
    op.create_index("ix_storage_locations_site_id", "storage_locations", ["site_id"])

    # ── inventory_balances ───────────────────────────────────────────
    op.create_table(
        "inventory_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "material_lot_id", postgresql.UUID(as_uuid=True), nullable=False,
        ),
        sa.Column(
            "location_id", postgresql.UUID(as_uuid=True), nullable=False,
        ),
        sa.Column(
            "quantity_on_hand", sa.Float(), nullable=False,
            server_default="0",
            comment="Current quantity at this location",
        ),
        sa.Column(
            "quantity_reserved", sa.Float(), nullable=False,
            server_default="0",
            comment="Quantity reserved for picking / orders",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["material_lot_id"], ["material_lots.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["storage_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_lot_id", "location_id",
            name="uq_inventory_balance_lot_location",
        ),
    )
    op.create_index("ix_inventory_balances_material_lot_id", "inventory_balances", ["material_lot_id"])
    op.create_index("ix_inventory_balances_location_id", "inventory_balances", ["location_id"])

    # ── inventory_transactions ───────────────────────────────────────
    op.create_table(
        "inventory_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "transaction_type", sa.String(20), nullable=False,
            comment="Transaction type: receive, putaway, pick, move, consume, adjust",
        ),
        sa.Column(
            "material_lot_id", postgresql.UUID(as_uuid=True), nullable=False,
        ),
        sa.Column(
            "from_location_id", postgresql.UUID(as_uuid=True), nullable=True,
            comment="Source location (null for receives)",
        ),
        sa.Column(
            "to_location_id", postgresql.UUID(as_uuid=True), nullable=True,
            comment="Destination location (null for consumes)",
        ),
        sa.Column(
            "quantity", sa.Float(), nullable=False,
            comment="Quantity moved (positive = into to_location)",
        ),
        sa.Column(
            "reference_id", postgresql.UUID(as_uuid=True), nullable=True,
            comment="Optional FK to production_order, unit, or lot",
        ),
        sa.Column(
            "reference_type", sa.String(30), nullable=True,
            comment="Type of reference: production_order, unit, lot",
        ),
        sa.Column(
            "reason", sa.String(255), nullable=True,
            comment="Reason or note for the transaction",
        ),
        sa.Column(
            "performed_at", sa.DateTime(timezone=True), nullable=False,
            comment="When the transaction was performed",
        ),
        sa.Column(
            "performed_at_utc", sa.DateTime(timezone=False), nullable=True,
            comment="When the transaction was performed (UTC naive)",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["material_lot_id"], ["material_lots.id"]),
        sa.ForeignKeyConstraint(["from_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["to_location_id"], ["storage_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_transactions_transaction_type", "inventory_transactions", ["transaction_type"])
    op.create_index("ix_inventory_transactions_material_lot_id", "inventory_transactions", ["material_lot_id"])
    op.create_index("ix_inventory_transactions_from_location_id", "inventory_transactions", ["from_location_id"])
    op.create_index("ix_inventory_transactions_to_location_id", "inventory_transactions", ["to_location_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_to_location_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_from_location_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_material_lot_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_transaction_type", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")

    op.drop_index("ix_inventory_balances_location_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_material_lot_id", table_name="inventory_balances")
    op.drop_table("inventory_balances")

    op.drop_index("ix_storage_locations_site_id", table_name="storage_locations")
    op.drop_index("ix_storage_locations_code", table_name="storage_locations")
    op.drop_index("ix_storage_locations_name", table_name="storage_locations")
    op.drop_table("storage_locations")
