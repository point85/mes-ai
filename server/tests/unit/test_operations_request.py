"""
Unit tests for the PROD-ORDER (Production Order) module.

Covers:
- Model instantiation & table mapping
- Schema validation (create, read, update, action schemas)
- Status transition logic (ORDER_TRANSITIONS)
- Event factories
- Exception construction
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.operations.models import OperationsRequest
from mes.core.operations.schemas import (
    OrderCreate,
    OrderRead,
    OrderUpdate,
    OrderReleaseRequest,
    OrderCompleteRequest,
    ORDER_STATUSES,
    ORDER_TRANSITIONS,
)
from mes.core.operations.events import (
    order_created,
    order_released,
    order_started,
    order_completed,
)
from mes.core.operations.exceptions import (
    DuplicateOrderNumberException,
    InvalidOrderTransitionException,
    OrderNotReleasedException,
)
from mes.core.operations.service import OperationsRequestService


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_order(**overrides) -> types.SimpleNamespace:
    """Create a lightweight order-like object for unit tests."""
    defaults = {
        "id": uuid.uuid4(),
        "order_number": "ORD-001",
        "product_id": uuid.uuid4(),
        "route_id": None,
        "quantity_ordered": 100,
        "quantity_completed": 0,
        "quantity_scrapped": 0,
        "status": "created",
        "priority": 0,
        "planned_start": None,
        "planned_end": None,
        "actual_start": None,
        "actual_end": None,
        "erp_reference": None,
        "notes": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


class TestProductionOrderModel:
    """Tests for the SQLAlchemy model."""

    def test_tablename(self):
        assert OperationsRequest.__tablename__ == "operations_requests"

    def test_has_mapper(self):
        assert hasattr(OperationsRequest, "__mapper__")

    def test_column_defaults(self):
        """Verify key column defaults are set."""
        cols = {c.name: c for c in OperationsRequest.__table__.columns}
        assert cols["status"].default.arg == "created"
        assert cols["priority"].default.arg == 0
        assert cols["quantity_completed"].default.arg == 0
        assert cols["quantity_scrapped"].default.arg == 0


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestOrderCreateSchema:
    def test_valid_create(self):
        pid = uuid.uuid4()
        data = OrderCreate(
            order_number="ORD-100", product_id=pid, quantity_ordered=50,
        )
        assert data.order_number == "ORD-100"
        assert data.product_id == pid
        assert data.quantity_ordered == 50
        assert data.priority == 0  # default
        assert data.route_id is None

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            OrderCreate(
                order_number="X", product_id=uuid.uuid4(), quantity_ordered=0,
            )

    def test_order_number_min_length(self):
        with pytest.raises(ValidationError):
            OrderCreate(
                order_number="", product_id=uuid.uuid4(), quantity_ordered=1,
            )

    def test_optional_fields(self):
        data = OrderCreate(
            order_number="ORD-200",
            product_id=uuid.uuid4(),
            quantity_ordered=10,
            route_id=uuid.uuid4(),
            priority=5,
            planned_start=datetime.now(timezone.utc),
            erp_reference="ERP-REF-001",
            notes="Test notes",
        )
        assert data.priority == 5
        assert data.erp_reference == "ERP-REF-001"
        assert data.route_id is not None


class TestOrderReadSchema:
    def test_from_attributes(self):
        order = _make_order()
        read = OrderRead.model_validate(order)
        assert read.order_number == "ORD-001"
        assert read.status == "created"
        assert read.quantity_ordered == 100
        assert read.quantity_completed == 0

    def test_all_fields_present(self):
        order = _make_order(
            erp_reference="ERP-001",
            notes="some notes",
            planned_start=datetime.now(timezone.utc),
            actual_start=datetime.now(timezone.utc),
        )
        read = OrderRead.model_validate(order)
        assert read.erp_reference == "ERP-001"
        assert read.actual_start is not None


class TestOrderUpdateSchema:
    def test_all_fields_optional(self):
        update = OrderUpdate()
        assert update.order_number is None
        assert update.quantity_ordered is None

    def test_partial_update(self):
        update = OrderUpdate(priority=10, notes="updated")
        assert update.priority == 10
        assert update.notes == "updated"

    def test_quantity_validation(self):
        with pytest.raises(ValidationError):
            OrderUpdate(quantity_ordered=-1)


class TestActionSchemas:
    def test_release_request(self):
        r = OrderReleaseRequest(notes="Ready")
        assert r.notes == "Ready"

    def test_release_request_optional(self):
        r = OrderReleaseRequest()
        assert r.notes is None

    def test_complete_request(self):
        c = OrderCompleteRequest(notes="All done")
        assert c.notes == "All done"


# ═════════════════════════════════════════════════════════════════════
# STATUS TRANSITION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestOrderTransitions:
    """Verify the ORDER_TRANSITIONS map is correct and complete."""

    def test_all_statuses_covered(self):
        assert set(ORDER_TRANSITIONS.keys()) == ORDER_STATUSES

    def test_created_can_release_or_close(self):
        assert ORDER_TRANSITIONS["created"] == {"released", "closed"}

    def test_released_can_start_or_close(self):
        assert ORDER_TRANSITIONS["released"] == {"in_progress", "closed"}

    def test_in_progress_can_complete_or_close(self):
        assert ORDER_TRANSITIONS["in_progress"] == {"completed", "closed"}

    def test_completed_can_close(self):
        assert ORDER_TRANSITIONS["completed"] == {"closed"}

    def test_closed_is_terminal(self):
        assert ORDER_TRANSITIONS["closed"] == set()

    def test_validate_transition_rejects_invalid(self):
        order = _make_order(status="created")
        with pytest.raises(InvalidOrderTransitionException):
            OperationsRequestService._validate_transition(order, "completed")

    def test_validate_transition_allows_valid(self):
        order = _make_order(status="created")
        # Should not raise
        OperationsRequestService._validate_transition(order, "released")


# ═════════════════════════════════════════════════════════════════════
# EVENT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestProductionOrderEvents:
    def test_order_created_event(self):
        ev = order_created("id1", "ORD-1", "prod-1")
        assert ev.event_type == "operations.request.created"
        assert ev.source == "operations"
        assert ev.payload["order_id"] == "id1"
        assert ev.payload["order_number"] == "ORD-1"

    def test_order_released_event(self):
        ev = order_released("id1", "prod-1", 100)
        assert ev.event_type == "operations.request.released"
        assert ev.payload["quantity"] == 100

    def test_order_started_event(self):
        ev = order_started("id1")
        assert ev.event_type == "operations.request.started"
        assert ev.payload["order_id"] == "id1"

    def test_order_completed_event(self):
        ev = order_completed("id1", 95)
        assert ev.event_type == "operations.request.completed"
        assert ev.payload["quantity_completed"] == 95


# ═════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestProductionOrderExceptions:
    def test_duplicate_order_number(self):
        ex = DuplicateOrderNumberException("ORD-001")
        assert ex.status_code == 409
        assert "ORD-001" in str(ex)
        assert ex.details["order_number"] == "ORD-001"

    def test_invalid_transition(self):
        ex = InvalidOrderTransitionException("ORD-001", "created", "completed")
        assert ex.status_code == 422
        assert "created" in str(ex)
        assert "completed" in str(ex)

    def test_order_not_released(self):
        ex = OrderNotReleasedException("ORD-001", "created")
        assert ex.status_code == 422
        assert "released" in str(ex)
