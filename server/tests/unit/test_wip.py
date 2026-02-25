"""
Unit tests for the WIP-TRACK (Work-In-Process Tracking) module.

Covers:
- Model instantiation & table mapping (Unit, Lot, UnitHistory, LotHistory)
- Schema validation (create, read, action request schemas)
- Event factories (unit and lot events)
- Exception construction
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.wip.models import Unit, Lot, UnitHistory, LotHistory
from mes.core.wip.schemas import (
    UnitCreate, UnitRead, LotCreate, LotRead,
    UnitHistoryRead, LotHistoryRead,
    StartRequest, CompleteRequest, MoveRequest,
    HoldRequest, ScrapRequest,
    UNIT_STATUSES, LOT_STATUSES,
)
from mes.core.wip.events import (
    unit_created, unit_started, unit_completed, unit_moved,
    unit_scrapped, unit_held, unit_released,
    lot_created, lot_started, lot_completed, lot_moved,
)
from mes.core.wip.exceptions import (
    DuplicateSerialNumberException,
    DuplicateLotNumberException,
    InvalidWIPTransitionException,
    NoRouteAssignedException,
    NoNextStepException,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_unit(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "serial_number": "SN-001",
        "order_id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "current_step_id": None,
        "current_equipment_id": None,
        "status": "queued",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_lot(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "lot_number": "LOT-001",
        "order_id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "quantity": 100,
        "current_step_id": None,
        "current_equipment_id": None,
        "status": "queued",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_unit_history(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "unit_id": uuid.uuid4(),
        "step_id": uuid.uuid4(),
        "equipment_id": None,
        "entered_at": datetime.now(timezone.utc),
        "exited_at": None,
        "result": None,
        "operator_id": None,
        "data_snapshot": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_lot_history(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "lot_id": uuid.uuid4(),
        "step_id": uuid.uuid4(),
        "equipment_id": None,
        "entered_at": datetime.now(timezone.utc),
        "exited_at": None,
        "quantity_in": 100,
        "quantity_out": 0,
        "quantity_scrapped": 0,
        "operator_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


class TestUnitModel:
    def test_tablename(self):
        assert Unit.__tablename__ == "units"

    def test_has_mapper(self):
        assert hasattr(Unit, "__mapper__")

    def test_default_status(self):
        cols = {c.name: c for c in Unit.__table__.columns}
        assert cols["status"].default.arg == "queued"


class TestLotModel:
    def test_tablename(self):
        assert Lot.__tablename__ == "lots"

    def test_has_mapper(self):
        assert hasattr(Lot, "__mapper__")

    def test_default_status(self):
        cols = {c.name: c for c in Lot.__table__.columns}
        assert cols["status"].default.arg == "queued"


class TestUnitHistoryModel:
    def test_tablename(self):
        assert UnitHistory.__tablename__ == "unit_history"

    def test_has_mapper(self):
        assert hasattr(UnitHistory, "__mapper__")


class TestLotHistoryModel:
    def test_tablename(self):
        assert LotHistory.__tablename__ == "lot_history"

    def test_has_mapper(self):
        assert hasattr(LotHistory, "__mapper__")

    def test_default_quantities(self):
        cols = {c.name: c for c in LotHistory.__table__.columns}
        assert cols["quantity_out"].default.arg == 0
        assert cols["quantity_scrapped"].default.arg == 0


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — UNIT
# ═════════════════════════════════════════════════════════════════════


class TestUnitCreateSchema:
    def test_valid_create(self):
        data = UnitCreate(
            serial_number="SN-100",
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        assert data.serial_number == "SN-100"

    def test_serial_number_required(self):
        with pytest.raises(ValidationError):
            UnitCreate(
                serial_number="",
                order_id=uuid.uuid4(),
                product_id=uuid.uuid4(),
            )

    def test_serial_number_max_length(self):
        with pytest.raises(ValidationError):
            UnitCreate(
                serial_number="X" * 201,
                order_id=uuid.uuid4(),
                product_id=uuid.uuid4(),
            )


class TestUnitReadSchema:
    def test_from_attributes(self):
        unit = _make_unit()
        read = UnitRead.model_validate(unit)
        assert read.serial_number == "SN-001"
        assert read.status == "queued"
        assert read.current_step_id is None

    def test_with_step_and_equipment(self):
        unit = _make_unit(
            current_step_id=uuid.uuid4(),
            current_equipment_id=uuid.uuid4(),
            status="in_process",
        )
        read = UnitRead.model_validate(unit)
        assert read.current_step_id is not None
        assert read.current_equipment_id is not None
        assert read.status == "in_process"


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — LOT
# ═════════════════════════════════════════════════════════════════════


class TestLotCreateSchema:
    def test_valid_create(self):
        data = LotCreate(
            lot_number="LOT-100",
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            quantity=50,
        )
        assert data.lot_number == "LOT-100"
        assert data.quantity == 50

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            LotCreate(
                lot_number="LOT-X",
                order_id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                quantity=0,
            )

    def test_lot_number_required(self):
        with pytest.raises(ValidationError):
            LotCreate(
                lot_number="",
                order_id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                quantity=10,
            )


class TestLotReadSchema:
    def test_from_attributes(self):
        lot = _make_lot()
        read = LotRead.model_validate(lot)
        assert read.lot_number == "LOT-001"
        assert read.quantity == 100
        assert read.status == "queued"


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — HISTORY
# ═════════════════════════════════════════════════════════════════════


class TestUnitHistoryReadSchema:
    def test_from_attributes(self):
        h = _make_unit_history(result="pass", exited_at=datetime.now(timezone.utc))
        read = UnitHistoryRead.model_validate(h)
        assert read.result == "pass"
        assert read.exited_at is not None

    def test_in_progress_record(self):
        h = _make_unit_history()
        read = UnitHistoryRead.model_validate(h)
        assert read.exited_at is None
        assert read.result is None


class TestLotHistoryReadSchema:
    def test_from_attributes(self):
        h = _make_lot_history(quantity_out=80, quantity_scrapped=5)
        read = LotHistoryRead.model_validate(h)
        assert read.quantity_in == 100
        assert read.quantity_out == 80
        assert read.quantity_scrapped == 5


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — ACTION REQUESTS
# ═════════════════════════════════════════════════════════════════════


class TestActionSchemas:
    def test_start_request_defaults(self):
        r = StartRequest()
        assert r.equipment_id is None

    def test_start_request_with_equipment(self):
        eq_id = uuid.uuid4()
        r = StartRequest(equipment_id=eq_id)
        assert r.equipment_id == eq_id

    def test_complete_request_defaults(self):
        r = CompleteRequest()
        assert r.result == "pass"
        assert r.data_snapshot is None

    def test_complete_request_with_data(self):
        r = CompleteRequest(
            result="fail",
            data_snapshot={"temp": 42.5},
            quantity_out=90,
            quantity_scrapped=10,
        )
        assert r.result == "fail"
        assert r.data_snapshot == {"temp": 42.5}
        assert r.quantity_out == 90

    def test_move_request_defaults(self):
        r = MoveRequest()
        assert r.target_step_id is None

    def test_move_request_with_target(self):
        sid = uuid.uuid4()
        r = MoveRequest(target_step_id=sid)
        assert r.target_step_id == sid

    def test_hold_request_requires_reason(self):
        with pytest.raises(ValidationError):
            HoldRequest(reason="")

    def test_hold_request_valid(self):
        r = HoldRequest(reason="Quality issue")
        assert r.reason == "Quality issue"

    def test_scrap_request_requires_reason(self):
        with pytest.raises(ValidationError):
            ScrapRequest(reason="")

    def test_scrap_request_valid(self):
        r = ScrapRequest(reason="Damaged beyond repair")
        assert r.reason == "Damaged beyond repair"

    def test_complete_request_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            CompleteRequest(quantity_out=0)


# ═════════════════════════════════════════════════════════════════════
# STATUS CONSTANTS
# ═════════════════════════════════════════════════════════════════════


class TestWIPStatuses:
    def test_unit_statuses(self):
        expected = {"queued", "in_process", "completed", "scrapped", "on_hold"}
        assert UNIT_STATUSES == expected

    def test_lot_statuses(self):
        expected = {"queued", "in_process", "completed", "scrapped", "on_hold"}
        assert LOT_STATUSES == expected


# ═════════════════════════════════════════════════════════════════════
# EVENT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestUnitEvents:
    def test_unit_created(self):
        ev = unit_created("u1", "o1", "SN-001")
        assert ev.event_type == "wip.unit.created"
        assert ev.source == "wip"
        assert ev.payload["serial_number"] == "SN-001"

    def test_unit_started(self):
        ev = unit_started("u1", "s1", "eq1")
        assert ev.event_type == "wip.unit.started"
        assert ev.payload["equipment_id"] == "eq1"

    def test_unit_completed(self):
        ev = unit_completed("u1", "s1", "pass")
        assert ev.event_type == "wip.unit.completed"
        assert ev.payload["result"] == "pass"

    def test_unit_moved(self):
        ev = unit_moved("u1", "s1", "s2")
        assert ev.event_type == "wip.unit.moved"
        assert ev.payload["from_step_id"] == "s1"
        assert ev.payload["to_step_id"] == "s2"

    def test_unit_scrapped(self):
        ev = unit_scrapped("u1", "s1", "damaged")
        assert ev.event_type == "wip.unit.scrapped"
        assert ev.payload["reason"] == "damaged"

    def test_unit_held(self):
        ev = unit_held("u1", "quality issue")
        assert ev.event_type == "wip.unit.held"
        assert ev.payload["reason"] == "quality issue"

    def test_unit_released(self):
        ev = unit_released("u1")
        assert ev.event_type == "wip.unit.released"


class TestLotEvents:
    def test_lot_created(self):
        ev = lot_created("l1", "o1", "LOT-001", 100)
        assert ev.event_type == "wip.lot.created"
        assert ev.payload["quantity"] == 100

    def test_lot_started(self):
        ev = lot_started("l1", "s1", None)
        assert ev.event_type == "wip.lot.started"
        assert ev.payload["equipment_id"] is None

    def test_lot_completed(self):
        ev = lot_completed("l1", "s1", 90, 10)
        assert ev.event_type == "wip.lot.completed"
        assert ev.payload["quantity_out"] == 90
        assert ev.payload["quantity_scrapped"] == 10

    def test_lot_moved(self):
        ev = lot_moved("l1", "s1", "s2")
        assert ev.event_type == "wip.lot.moved"


# ═════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestWIPExceptions:
    def test_duplicate_serial_number(self):
        ex = DuplicateSerialNumberException("SN-001")
        assert ex.status_code == 409
        assert "SN-001" in str(ex)

    def test_duplicate_lot_number(self):
        ex = DuplicateLotNumberException("LOT-001")
        assert ex.status_code == 409
        assert "LOT-001" in str(ex)

    def test_invalid_wip_transition(self):
        ex = InvalidWIPTransitionException("SN-001", "completed", "start")
        assert ex.status_code == 422
        assert "completed" in str(ex)
        assert "start" in str(ex)

    def test_no_route_assigned(self):
        ex = NoRouteAssignedException("order-id")
        assert ex.status_code == 422
        assert "order-id" in str(ex)

    def test_no_next_step(self):
        ex = NoNextStepException("SN-001", "step-id")
        assert ex.status_code == 422
        assert "SN-001" in str(ex)
