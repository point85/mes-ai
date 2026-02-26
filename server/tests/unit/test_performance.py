"""
Unit tests for PERF-ANALYSIS (Performance Analysis) module.

Covers:
- Model table names, columns, and repr
- Schema validation for EquipmentStateLog, ProductionCounter, OEE
- Event factory functions
- Exception construction
- Service / route imports
- Constants validation
"""

from __future__ import annotations

import types
import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.performance.events import (
    equipment_state_changed,
    oee_calculated,
)
from mes.core.performance.exceptions import (
    NoCounterDataException,
    NoStateLogDataException,
)
from mes.core.performance.models import (
    EquipmentStateLog,
    ProductionCounter,
)
from mes.core.performance.schemas import (
    DISPATCH_CATEGORIES,
    OEE_BUCKETS,
    CounterCreateUpdate,
    EquipmentStateLogRead,
    OEEResult,
    ProductionCounterRead,
    StateChangeRequest,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_state_log(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "equipment_id": uuid.uuid4(),
        "state_model": "default",
        "state": "Idle",
        "sub_state": None,
        "dispatch_category": "available",
        "oee_bucket": "uptime_non_value",
        "started_at": datetime.now(timezone.utc),
        "ended_at": None,
        "reason_code": None,
        "notes": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_counter(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "equipment_id": uuid.uuid4(),
        "order_id": uuid.uuid4(),
        "shift_date": date.today(),
        "good_count": 100,
        "reject_count": 5,
        "rework_count": 3,
        "ideal_cycle_time_sec": 30.0,
        "actual_run_time_sec": 3600.0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═══════════════════════════════════════════════════════════════════
# Model Tests
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentStateLogModel:
    def test_tablename(self):
        assert EquipmentStateLog.__tablename__ == "equipment_state_logs"

    def test_mapper_columns(self):
        cols = {c.key for c in EquipmentStateLog.__table__.columns}
        assert "equipment_id" in cols
        assert "state_model" in cols
        assert "state" in cols
        assert "dispatch_category" in cols
        assert "oee_bucket" in cols
        assert "started_at" in cols
        assert "ended_at" in cols

    def test_repr(self):
        log = EquipmentStateLog()
        log.id = uuid.uuid4()
        log.equipment_id = uuid.uuid4()
        log.state = "Execute"
        log.dispatch_category = "busy"
        r = repr(log)
        assert "Execute" in r
        assert "busy" in r


class TestProductionCounterModel:
    def test_tablename(self):
        assert ProductionCounter.__tablename__ == "production_counters"

    def test_mapper_columns(self):
        cols = {c.key for c in ProductionCounter.__table__.columns}
        assert "equipment_id" in cols
        assert "order_id" in cols
        assert "shift_date" in cols
        assert "good_count" in cols
        assert "reject_count" in cols
        assert "rework_count" in cols
        assert "ideal_cycle_time_sec" in cols
        assert "actual_run_time_sec" in cols

    def test_repr(self):
        c = ProductionCounter()
        c.id = uuid.uuid4()
        c.equipment_id = uuid.uuid4()
        c.shift_date = date.today()
        c.good_count = 50
        r = repr(c)
        assert "50" in r


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — EquipmentStateLog
# ═══════════════════════════════════════════════════════════════════


class TestStateChangeRequestSchema:
    def test_valid_request(self):
        schema = StateChangeRequest(
            equipment_id=uuid.uuid4(),
            state="Execute",
            dispatch_category="busy",
            oee_bucket="uptime_value_add",
            started_at=datetime.now(timezone.utc),
        )
        assert schema.state_model == "default"
        assert schema.dispatch_category == "busy"

    def test_invalid_dispatch_category(self):
        with pytest.raises(ValidationError, match="dispatch_category"):
            StateChangeRequest(
                equipment_id=uuid.uuid4(),
                state="X",
                dispatch_category="invalid",
                oee_bucket="uptime_value_add",
                started_at=datetime.now(timezone.utc),
            )

    def test_invalid_oee_bucket(self):
        with pytest.raises(ValidationError, match="oee_bucket"):
            StateChangeRequest(
                equipment_id=uuid.uuid4(),
                state="X",
                dispatch_category="available",
                oee_bucket="invalid",
                started_at=datetime.now(timezone.utc),
            )

    def test_all_dispatch_categories(self):
        for cat in DISPATCH_CATEGORIES:
            schema = StateChangeRequest(
                equipment_id=uuid.uuid4(),
                state="S",
                dispatch_category=cat,
                oee_bucket="uptime_value_add",
                started_at=datetime.now(timezone.utc),
            )
            assert schema.dispatch_category == cat

    def test_all_oee_buckets(self):
        for bucket in OEE_BUCKETS:
            schema = StateChangeRequest(
                equipment_id=uuid.uuid4(),
                state="S",
                dispatch_category="available",
                oee_bucket=bucket,
                started_at=datetime.now(timezone.utc),
            )
            assert schema.oee_bucket == bucket

    def test_read_from_attributes(self):
        obj = _make_state_log()
        schema = EquipmentStateLogRead.model_validate(obj, from_attributes=True)
        assert schema.state == "Idle"
        assert schema.ended_at is None


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — ProductionCounter
# ═══════════════════════════════════════════════════════════════════


class TestCounterSchemas:
    def test_create_minimal(self):
        schema = CounterCreateUpdate(
            equipment_id=uuid.uuid4(),
            shift_date=date.today(),
        )
        assert schema.good_count == 0
        assert schema.reject_count == 0

    def test_create_full(self):
        schema = CounterCreateUpdate(
            equipment_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            shift_date=date.today(),
            good_count=100,
            reject_count=5,
            rework_count=3,
            ideal_cycle_time_sec=30.0,
            actual_run_time_sec=3600.0,
        )
        assert schema.good_count == 100

    def test_negative_good_count_fails(self):
        with pytest.raises(ValidationError):
            CounterCreateUpdate(
                equipment_id=uuid.uuid4(),
                shift_date=date.today(),
                good_count=-1,
            )

    def test_negative_cycle_time_fails(self):
        with pytest.raises(ValidationError):
            CounterCreateUpdate(
                equipment_id=uuid.uuid4(),
                shift_date=date.today(),
                ideal_cycle_time_sec=-5.0,
            )

    def test_read_from_attributes(self):
        obj = _make_counter()
        schema = ProductionCounterRead.model_validate(obj, from_attributes=True)
        assert schema.good_count == 100


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — OEEResult
# ═══════════════════════════════════════════════════════════════════


class TestOEEResultSchema:
    def test_valid_oee(self):
        result = OEEResult(
            equipment_id=uuid.uuid4(),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            availability=0.85,
            performance=0.90,
            quality=0.95,
            oee=0.7268,
        )
        assert result.oee == 0.7268

    def test_zero_oee(self):
        result = OEEResult(
            equipment_id=uuid.uuid4(),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            availability=0.0,
            performance=0.0,
            quality=0.0,
            oee=0.0,
        )
        assert result.oee == 0.0


# ═══════════════════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════════════════


class TestPerformanceConstants:
    def test_dispatch_categories(self):
        expected = {"available", "busy", "unavailable_planned", "unavailable_unplanned"}
        assert DISPATCH_CATEGORIES == expected

    def test_oee_buckets(self):
        expected = {
            "uptime_value_add", "uptime_non_value",
            "downtime_planned", "downtime_unplanned", "excluded",
        }
        assert OEE_BUCKETS == expected


# ═══════════════════════════════════════════════════════════════════
# Event Tests
# ═══════════════════════════════════════════════════════════════════


class TestPerformanceEvents:
    def test_equipment_state_changed(self):
        ev = equipment_state_changed("eq1", "Execute", "busy")
        assert ev.event_type == "equipment.state.changed"
        assert ev.payload["state"] == "Execute"
        assert ev.payload["dispatch_category"] == "busy"

    def test_oee_calculated(self):
        ev = oee_calculated("eq1", 0.85)
        assert ev.event_type == "performance.oee.calculated"
        assert ev.payload["oee"] == 0.85


# ═══════════════════════════════════════════════════════════════════
# Exception Tests
# ═══════════════════════════════════════════════════════════════════


class TestPerformanceExceptions:
    def test_no_state_log_data(self):
        exc = NoStateLogDataException("eq-1", "2026-02-25")
        assert exc.status_code == 404
        assert exc.error_code == "NO_STATE_LOG_DATA"
        assert "eq-1" in str(exc)

    def test_no_counter_data(self):
        exc = NoCounterDataException("eq-1", "2026-02-25")
        assert exc.status_code == 404
        assert exc.error_code == "NO_COUNTER_DATA"


# ═══════════════════════════════════════════════════════════════════
# Service / Route Import Tests
# ═══════════════════════════════════════════════════════════════════


class TestServiceAndRouteImports:
    def test_equipment_state_service_methods(self):
        from mes.core.performance.service import EquipmentStateService
        assert hasattr(EquipmentStateService, "record_state_change")
        assert hasattr(EquipmentStateService, "list_state_logs")
        assert hasattr(EquipmentStateService, "get_current_state")

    def test_counter_service_methods(self):
        from mes.core.performance.service import ProductionCounterService
        assert hasattr(ProductionCounterService, "create_or_update_counter")
        assert hasattr(ProductionCounterService, "list_counters")

    def test_oee_service_methods(self):
        from mes.core.performance.service import OEEService
        assert hasattr(OEEService, "calculate_oee")

    def test_router_paths(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/performance/oee" in paths
        assert "/api/v1/performance/equipment-states" in paths
        assert "/api/v1/performance/counters" in paths
