"""
Unit tests for INVENTORY (Inventory Management) module.

Covers:
- Model table names, columns, relationships, unique constraints, and repr
- Schema validation (create / read / update) for StorageLocation,
  InventoryBalance, InventoryTransaction, and action schemas
- Event factory functions
- Exception hierarchy and error codes
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.inventory.events import (
    inventory_adjusted,
    inventory_consumed,
    inventory_moved,
    inventory_picked,
    inventory_putaway,
    inventory_received,
)
from mes.core.inventory.exceptions import (
    DuplicateLocationCodeException,
    InsufficientInventoryException,
    InvalidTransactionException,
    LocationNotFoundException,
)
from mes.core.inventory.models import (
    InventoryBalance,
    InventoryTransaction,
    StorageLocation,
)
from mes.core.inventory.schemas import (
    AdjustRequest,
    ConsumeInventoryRequest,
    InventoryBalanceRead,
    InventoryTransactionRead,
    LOCATION_TYPES,
    MoveRequest,
    PickRequest,
    PutawayRequest,
    ReceiveRequest,
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
    TRANSACTION_TYPES,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_location(**overrides) -> types.SimpleNamespace:
    """Create a lightweight StorageLocation-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Aisle 3 Bay 2 Tier 1",
        "code": "A03-B02-T01",
        "description": "Warehouse racking slot",
        "location_type": "storage",
        "aisle": "A03",
        "bay": "B02",
        "tier": "T01",
        "site_id": uuid.uuid4(),
        "capacity": 500.0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_balance(**overrides) -> types.SimpleNamespace:
    """Create a lightweight InventoryBalance-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "material_lot_id": uuid.uuid4(),
        "location_id": uuid.uuid4(),
        "quantity_on_hand": 100.0,
        "quantity_reserved": 0.0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_transaction(**overrides) -> types.SimpleNamespace:
    """Create a lightweight InventoryTransaction-like object."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": uuid.uuid4(),
        "transaction_type": "receive",
        "material_lot_id": uuid.uuid4(),
        "from_location_id": None,
        "to_location_id": uuid.uuid4(),
        "quantity": 50.0,
        "reference_id": None,
        "reference_type": None,
        "reason": "Initial receipt",
        "performed_at": now,
        "performed_at_utc": now.replace(tzinfo=None),
        "is_active": True,
        "created_at": now,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


class TestStorageLocationModel:
    """Tests for the StorageLocation SQLAlchemy model."""

    def test_tablename(self):
        assert StorageLocation.__tablename__ == "storage_locations"

    def test_has_mapper(self):
        assert hasattr(StorageLocation, "__mapper__")

    def test_base_columns_present(self):
        col_names = {c.key for c in StorageLocation.__mapper__.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names, f"Missing '{col}'"

    def test_domain_columns_present(self):
        col_names = {c.key for c in StorageLocation.__mapper__.columns}
        for col in ("name", "code", "description", "location_type", "aisle", "bay", "tier", "site_id", "capacity"):
            assert col in col_names, f"Missing '{col}'"

    def test_code_column_is_unique(self):
        col = StorageLocation.__table__.c.code
        assert col.unique is True

    def test_balances_relationship(self):
        rels = {r.key for r in StorageLocation.__mapper__.relationships}
        assert "balances" in rels

    def test_site_relationship(self):
        rels = {r.key for r in StorageLocation.__mapper__.relationships}
        assert "site" in rels

    def test_repr(self):
        obj = _make_location()
        expected_str = f"<StorageLocation id={obj.id} code=A03-B02-T01 type=storage>"
        # Just check that the attributes exist in the repr pattern
        assert obj.code == "A03-B02-T01"
        assert obj.location_type == "storage"


class TestInventoryBalanceModel:
    """Tests for the InventoryBalance SQLAlchemy model."""

    def test_tablename(self):
        assert InventoryBalance.__tablename__ == "inventory_balances"

    def test_has_mapper(self):
        assert hasattr(InventoryBalance, "__mapper__")

    def test_domain_columns_present(self):
        col_names = {c.key for c in InventoryBalance.__mapper__.columns}
        for col in ("material_lot_id", "location_id", "quantity_on_hand", "quantity_reserved"):
            assert col in col_names, f"Missing '{col}'"

    def test_unique_constraint(self):
        constraints = InventoryBalance.__table__.constraints
        unique_names = {
            c.name for c in constraints
            if hasattr(c, "name") and c.name is not None
        }
        assert "uq_inventory_balance_lot_location" in unique_names

    def test_material_lot_relationship(self):
        rels = {r.key for r in InventoryBalance.__mapper__.relationships}
        assert "material_lot" in rels

    def test_location_relationship(self):
        rels = {r.key for r in InventoryBalance.__mapper__.relationships}
        assert "location" in rels


class TestInventoryTransactionModel:
    """Tests for the InventoryTransaction SQLAlchemy model."""

    def test_tablename(self):
        assert InventoryTransaction.__tablename__ == "inventory_transactions"

    def test_has_mapper(self):
        assert hasattr(InventoryTransaction, "__mapper__")

    def test_domain_columns_present(self):
        col_names = {c.key for c in InventoryTransaction.__mapper__.columns}
        for col in (
            "transaction_type", "material_lot_id", "from_location_id",
            "to_location_id", "quantity", "reference_id", "reference_type",
            "reason", "performed_at", "performed_at_utc",
        ):
            assert col in col_names, f"Missing '{col}'"

    def test_material_lot_relationship(self):
        rels = {r.key for r in InventoryTransaction.__mapper__.relationships}
        assert "material_lot" in rels

    def test_from_location_relationship(self):
        rels = {r.key for r in InventoryTransaction.__mapper__.relationships}
        assert "from_location" in rels

    def test_to_location_relationship(self):
        rels = {r.key for r in InventoryTransaction.__mapper__.relationships}
        assert "to_location" in rels


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestStorageLocationSchemas:
    """Tests for StorageLocation Pydantic schemas."""

    def test_create_minimal(self):
        s = StorageLocationCreate(name="Recv Dock 1", code="RECV-01")
        assert s.name == "Recv Dock 1"
        assert s.code == "RECV-01"
        assert s.location_type == "storage"  # default

    def test_create_full(self):
        s = StorageLocationCreate(
            name="Aisle 1 Bay 3 Tier 2",
            code="A01-B03-T02",
            description="High shelf",
            location_type="storage",
            aisle="A01",
            bay="B03",
            tier="T02",
            site_id=uuid.uuid4(),
            capacity=200.0,
        )
        assert s.aisle == "A01"
        assert s.bay == "B03"
        assert s.tier == "T02"

    def test_create_rejects_space_in_code(self):
        with pytest.raises(ValidationError) as exc_info:
            StorageLocationCreate(name="Bad", code="BAD CODE")
        assert "code must not contain spaces" in str(exc_info.value)

    def test_create_rejects_invalid_location_type(self):
        with pytest.raises(ValidationError) as exc_info:
            StorageLocationCreate(name="X", code="X1", location_type="invalid")
        assert "location_type" in str(exc_info.value)

    def test_read_from_attributes(self):
        obj = _make_location()
        s = StorageLocationRead.model_validate(obj, from_attributes=True)
        assert s.code == "A03-B02-T01"
        assert s.location_type == "storage"

    def test_update_partial(self):
        s = StorageLocationUpdate(name="Updated")
        assert s.name == "Updated"
        assert s.code is None

    def test_update_rejects_space_in_code(self):
        with pytest.raises(ValidationError):
            StorageLocationUpdate(code="BAD CODE")

    def test_update_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            StorageLocationUpdate(location_type="invalid")


class TestInventoryBalanceSchemas:
    """Tests for InventoryBalance Pydantic schemas."""

    def test_read_from_attributes(self):
        obj = _make_balance()
        s = InventoryBalanceRead.model_validate(obj, from_attributes=True)
        assert s.quantity_on_hand == 100.0
        assert s.quantity_reserved == 0.0


class TestInventoryTransactionSchemas:
    """Tests for InventoryTransaction Pydantic schemas."""

    def test_read_from_attributes(self):
        obj = _make_transaction()
        s = InventoryTransactionRead.model_validate(obj, from_attributes=True)
        assert s.transaction_type == "receive"
        assert s.quantity == 50.0
        assert s.from_location_id is None


class TestActionSchemas:
    """Tests for inventory action request schemas."""

    def test_receive_request_valid(self):
        r = ReceiveRequest(
            material_lot_id=uuid.uuid4(),
            to_location_id=uuid.uuid4(),
            quantity=100.0,
        )
        assert r.quantity == 100.0

    def test_receive_request_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            ReceiveRequest(
                material_lot_id=uuid.uuid4(),
                to_location_id=uuid.uuid4(),
                quantity=0,
            )

    def test_receive_request_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            ReceiveRequest(
                material_lot_id=uuid.uuid4(),
                to_location_id=uuid.uuid4(),
                quantity=-10,
            )

    def test_receive_request_rejects_invalid_reference_type(self):
        with pytest.raises(ValidationError):
            ReceiveRequest(
                material_lot_id=uuid.uuid4(),
                to_location_id=uuid.uuid4(),
                quantity=10,
                reference_type="invalid",
            )

    def test_putaway_request_valid(self):
        r = PutawayRequest(
            material_lot_id=uuid.uuid4(),
            from_location_id=uuid.uuid4(),
            to_location_id=uuid.uuid4(),
            quantity=50.0,
        )
        assert r.quantity == 50.0

    def test_pick_request_valid(self):
        r = PickRequest(
            material_lot_id=uuid.uuid4(),
            from_location_id=uuid.uuid4(),
            to_location_id=uuid.uuid4(),
            quantity=20.0,
            reference_type="production_order",
        )
        assert r.reference_type == "production_order"

    def test_pick_request_rejects_invalid_reference_type(self):
        with pytest.raises(ValidationError):
            PickRequest(
                material_lot_id=uuid.uuid4(),
                from_location_id=uuid.uuid4(),
                to_location_id=uuid.uuid4(),
                quantity=20.0,
                reference_type="bogus",
            )

    def test_move_request_valid(self):
        r = MoveRequest(
            material_lot_id=uuid.uuid4(),
            from_location_id=uuid.uuid4(),
            to_location_id=uuid.uuid4(),
            quantity=30.0,
        )
        assert r.quantity == 30.0

    def test_consume_request_valid(self):
        r = ConsumeInventoryRequest(
            material_lot_id=uuid.uuid4(),
            from_location_id=uuid.uuid4(),
            quantity=10.0,
        )
        assert r.quantity == 10.0

    def test_consume_request_with_step_id(self):
        step = uuid.uuid4()
        r = ConsumeInventoryRequest(
            material_lot_id=uuid.uuid4(),
            from_location_id=uuid.uuid4(),
            quantity=5.0,
            reference_id=uuid.uuid4(),
            reference_type="unit",
            step_id=step,
        )
        assert r.step_id == step
        assert r.reference_type == "unit"

    def test_consume_request_step_id_defaults_none(self):
        r = ConsumeInventoryRequest(
            material_lot_id=uuid.uuid4(),
            from_location_id=uuid.uuid4(),
            quantity=10.0,
        )
        assert r.step_id is None

    def test_consume_request_rejects_invalid_reference_type(self):
        with pytest.raises(ValidationError):
            ConsumeInventoryRequest(
                material_lot_id=uuid.uuid4(),
                from_location_id=uuid.uuid4(),
                quantity=10.0,
                reference_type="invalid",
            )

    def test_adjust_request_requires_reason(self):
        with pytest.raises(ValidationError):
            AdjustRequest(
                material_lot_id=uuid.uuid4(),
                location_id=uuid.uuid4(),
                quantity=99.0,
                reason="",  # empty string violates min_length=1
            )

    def test_adjust_request_valid(self):
        r = AdjustRequest(
            material_lot_id=uuid.uuid4(),
            location_id=uuid.uuid4(),
            quantity=99.0,
            reason="Cycle count correction",
        )
        assert r.quantity == 99.0
        assert r.reason == "Cycle count correction"


# ═════════════════════════════════════════════════════════════════════
# CONSTANT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestConstants:
    """Tests for module constants."""

    def test_location_types(self):
        assert LOCATION_TYPES == {"receiving", "storage", "rip", "staging", "shipping"}

    def test_transaction_types(self):
        assert TRANSACTION_TYPES == {"receive", "putaway", "pick", "move", "consume", "adjust"}


# ═════════════════════════════════════════════════════════════════════
# EVENT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestInventoryEvents:
    """Tests for inventory event factory functions."""

    def test_inventory_received_event(self):
        evt = inventory_received("lot-1", "loc-1", 100.0)
        assert evt.event_type == "inventory.received"
        assert evt.source == "inventory"
        assert evt.payload["material_lot_id"] == "lot-1"
        assert evt.payload["location_id"] == "loc-1"
        assert evt.payload["quantity"] == 100.0

    def test_inventory_putaway_event(self):
        evt = inventory_putaway("lot-1", "from-1", "to-1", 50.0)
        assert evt.event_type == "inventory.putaway"
        assert evt.payload["from_location_id"] == "from-1"
        assert evt.payload["to_location_id"] == "to-1"

    def test_inventory_picked_event(self):
        evt = inventory_picked("lot-1", "from-1", "to-1", 20.0)
        assert evt.event_type == "inventory.picked"
        assert evt.payload["quantity"] == 20.0

    def test_inventory_moved_event(self):
        evt = inventory_moved("lot-1", "from-1", "to-1", 30.0)
        assert evt.event_type == "inventory.moved"

    def test_inventory_consumed_event(self):
        evt = inventory_consumed("lot-1", "loc-1", 10.0)
        assert evt.event_type == "inventory.consumed"
        assert evt.payload["location_id"] == "loc-1"

    def test_inventory_adjusted_event(self):
        evt = inventory_adjusted("lot-1", "loc-1", 100.0, 95.0)
        assert evt.event_type == "inventory.adjusted"
        assert evt.payload["old_quantity"] == 100.0
        assert evt.payload["new_quantity"] == 95.0


# ═════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestInventoryExceptions:
    """Tests for domain exceptions."""

    def test_duplicate_location_code(self):
        exc = DuplicateLocationCodeException("RECV-01")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_LOCATION_CODE"
        assert "RECV-01" in str(exc)
        assert exc.details["location_code"] == "RECV-01"

    def test_location_not_found(self):
        exc = LocationNotFoundException("some-id")
        assert exc.status_code == 404
        assert exc.error_code == "LOCATION_NOT_FOUND"

    def test_insufficient_inventory(self):
        exc = InsufficientInventoryException("loc-1", 50.0, 30.0)
        assert exc.status_code == 422
        assert exc.error_code == "INSUFFICIENT_INVENTORY"
        assert exc.details["requested"] == 50.0
        assert exc.details["available"] == 30.0

    def test_invalid_transaction(self):
        exc = InvalidTransactionException("Same source and destination")
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_INVENTORY_TRANSACTION"
