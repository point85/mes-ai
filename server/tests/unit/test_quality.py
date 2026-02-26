"""
Unit tests for QUAL-MGMT (Quality Management) module.

Covers:
- Model table names, columns, relationships, and repr
- Schema validation (create / read / update) for QualityTest, TestResult, NonConformance
- Event factory functions
- Exception hierarchy and error codes
- NC transition state machine
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.quality.events import (
    quality_nc_created,
    quality_nc_resolved,
    quality_test_failed,
    quality_test_passed,
)
from mes.core.quality.exceptions import (
    DispositionRequiredException,
    DuplicateTestCodeException,
    InvalidNCTransitionException,
)
from mes.core.quality.models import (
    NonConformance,
    QualityTest,
    TestResult,
)
from mes.core.quality.schemas import (
    NC_STATUSES,
    NC_TRANSITIONS,
    NC_TYPES,
    DISPOSITIONS,
    TEST_RESULTS,
    TEST_TYPES,
    NonConformanceCreate,
    NonConformanceRead,
    NonConformanceUpdate,
    QualityTestCreate,
    QualityTestRead,
    QualityTestUpdate,
    RecordResultRequest,
    TestResultRead,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_quality_test(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Dimension Check",
        "code": "DIM-CHK-001",
        "description": "Check widget dimensions",
        "test_type": "inline",
        "step_id": uuid.uuid4(),
        "parameters": {"tolerance_mm": 0.5},
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_test_result(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "test_id": uuid.uuid4(),
        "unit_id": uuid.uuid4(),
        "lot_id": None,
        "result": "pass",
        "measured_values": {"dimension_a": 10.5},
        "operator_id": uuid.uuid4(),
        "equipment_id": uuid.uuid4(),
        "tested_at": datetime.now(timezone.utc),
        "notes": "Within tolerance",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_nc(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "unit_id": uuid.uuid4(),
        "lot_id": None,
        "step_id": uuid.uuid4(),
        "nc_type": "defect",
        "description": "Scratched surface",
        "disposition": None,
        "status": "open",
        "resolved_at": None,
        "resolved_by_id": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═══════════════════════════════════════════════════════════════════
# Model Tests
# ═══════════════════════════════════════════════════════════════════


class TestQualityTestModel:
    def test_tablename(self):
        assert QualityTest.__tablename__ == "quality_tests"

    def test_mapper_columns(self):
        cols = {c.key for c in QualityTest.__table__.columns}
        assert "name" in cols
        assert "code" in cols
        assert "test_type" in cols
        assert "step_id" in cols
        assert "parameters" in cols

    def test_repr(self):
        t = QualityTest()
        t.id = uuid.uuid4()
        t.code = "TST-1"
        t.test_type = "inline"
        r = repr(t)
        assert "TST-1" in r
        assert "inline" in r

    def test_results_relationship(self):
        assert hasattr(QualityTest, "results")


class TestTestResultModel:
    def test_tablename(self):
        assert TestResult.__tablename__ == "test_results"

    def test_mapper_columns(self):
        cols = {c.key for c in TestResult.__table__.columns}
        assert "test_id" in cols
        assert "unit_id" in cols
        assert "lot_id" in cols
        assert "result" in cols
        assert "measured_values" in cols
        assert "tested_at" in cols

    def test_repr(self):
        tr = TestResult()
        tr.id = uuid.uuid4()
        tr.test_id = uuid.uuid4()
        tr.result = "fail"
        r = repr(tr)
        assert "fail" in r


class TestNonConformanceModel:
    def test_tablename(self):
        assert NonConformance.__tablename__ == "non_conformances"

    def test_mapper_columns(self):
        cols = {c.key for c in NonConformance.__table__.columns}
        assert "unit_id" in cols
        assert "nc_type" in cols
        assert "disposition" in cols
        assert "status" in cols
        assert "resolved_at" in cols

    def test_repr(self):
        nc = NonConformance()
        nc.id = uuid.uuid4()
        nc.nc_type = "defect"
        nc.status = "open"
        r = repr(nc)
        assert "defect" in r
        assert "open" in r


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — QualityTest
# ═══════════════════════════════════════════════════════════════════


class TestQualityTestSchemas:
    def test_create_minimal(self):
        schema = QualityTestCreate(name="Test A", code="TST-A")
        assert schema.test_type == "inline"
        assert schema.step_id is None

    def test_create_full(self):
        sid = uuid.uuid4()
        schema = QualityTestCreate(
            name="Test B", code="TST-B", description="Full test",
            test_type="destructive", step_id=sid,
            parameters={"tol": 1.0},
        )
        assert schema.test_type == "destructive"
        assert schema.step_id == sid

    def test_create_invalid_test_type(self):
        with pytest.raises(ValidationError, match="test_type"):
            QualityTestCreate(name="X", code="X", test_type="unknown")

    def test_create_code_no_whitespace(self):
        with pytest.raises(ValidationError, match="code"):
            QualityTestCreate(name="X", code="bad code")

    def test_read_from_attributes(self):
        obj = _make_quality_test()
        schema = QualityTestRead.model_validate(obj, from_attributes=True)
        assert schema.code == "DIM-CHK-001"

    def test_update_all_optional(self):
        schema = QualityTestUpdate()
        assert schema.name is None
        assert schema.test_type is None

    def test_update_invalid_test_type(self):
        with pytest.raises(ValidationError, match="test_type"):
            QualityTestUpdate(test_type="bad")


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — TestResult
# ═══════════════════════════════════════════════════════════════════


class TestTestResultSchemas:
    def test_record_result_pass(self):
        now = datetime.now(timezone.utc)
        schema = RecordResultRequest(
            test_id=uuid.uuid4(), result="pass", tested_at=now,
        )
        assert schema.result == "pass"

    def test_record_result_fail(self):
        now = datetime.now(timezone.utc)
        schema = RecordResultRequest(
            test_id=uuid.uuid4(), result="fail", tested_at=now,
        )
        assert schema.result == "fail"

    def test_record_result_invalid(self):
        with pytest.raises(ValidationError, match="result"):
            RecordResultRequest(
                test_id=uuid.uuid4(), result="maybe",
                tested_at=datetime.now(timezone.utc),
            )

    def test_record_result_with_unit_and_lot(self):
        now = datetime.now(timezone.utc)
        schema = RecordResultRequest(
            test_id=uuid.uuid4(), result="pass", tested_at=now,
            unit_id=uuid.uuid4(), lot_id=uuid.uuid4(),
            measured_values={"dim": 10.0},
        )
        assert schema.measured_values == {"dim": 10.0}

    def test_read_from_attributes(self):
        obj = _make_test_result()
        schema = TestResultRead.model_validate(obj, from_attributes=True)
        assert schema.result == "pass"


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — NonConformance
# ═══════════════════════════════════════════════════════════════════


class TestNonConformanceSchemas:
    def test_create_minimal(self):
        schema = NonConformanceCreate(
            nc_type="defect", description="Scratch found",
        )
        assert schema.unit_id is None
        assert schema.nc_type == "defect"

    def test_create_full(self):
        uid = uuid.uuid4()
        sid = uuid.uuid4()
        schema = NonConformanceCreate(
            unit_id=uid, step_id=sid,
            nc_type="out_of_spec", description="Dimension out of spec",
        )
        assert schema.unit_id == uid

    def test_create_invalid_nc_type(self):
        with pytest.raises(ValidationError, match="nc_type"):
            NonConformanceCreate(nc_type="invalid", description="test")

    def test_create_empty_description_fails(self):
        with pytest.raises(ValidationError):
            NonConformanceCreate(nc_type="defect", description="")

    def test_read_from_attributes(self):
        obj = _make_nc()
        schema = NonConformanceRead.model_validate(obj, from_attributes=True)
        assert schema.status == "open"
        assert schema.disposition is None

    def test_update_disposition(self):
        schema = NonConformanceUpdate(disposition="rework")
        assert schema.disposition == "rework"

    def test_update_invalid_status(self):
        with pytest.raises(ValidationError, match="status"):
            NonConformanceUpdate(status="invalid")

    def test_update_invalid_disposition(self):
        with pytest.raises(ValidationError, match="disposition"):
            NonConformanceUpdate(disposition="invalid")

    def test_all_dispositions_valid(self):
        for d in DISPOSITIONS:
            schema = NonConformanceUpdate(disposition=d)
            assert schema.disposition == d

    def test_all_nc_statuses_valid(self):
        for s in NC_STATUSES:
            schema = NonConformanceUpdate(status=s)
            assert schema.status == s


# ═══════════════════════════════════════════════════════════════════
# NC Transition Tests
# ═══════════════════════════════════════════════════════════════════


class TestNCTransitions:
    def test_open_can_go_to_investigating(self):
        assert "investigating" in NC_TRANSITIONS["open"]

    def test_open_can_go_to_resolved(self):
        assert "resolved" in NC_TRANSITIONS["open"]

    def test_open_can_go_to_closed(self):
        assert "closed" in NC_TRANSITIONS["open"]

    def test_investigating_can_go_to_resolved(self):
        assert "resolved" in NC_TRANSITIONS["investigating"]

    def test_investigating_can_go_to_closed(self):
        assert "closed" in NC_TRANSITIONS["investigating"]

    def test_resolved_can_go_to_closed(self):
        assert "closed" in NC_TRANSITIONS["resolved"]

    def test_closed_cannot_transition(self):
        assert NC_TRANSITIONS["closed"] == set()

    def test_all_statuses_in_transitions(self):
        assert set(NC_TRANSITIONS.keys()) == NC_STATUSES


# ═══════════════════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════════════════


class TestConstants:
    def test_test_types(self):
        assert TEST_TYPES == {"inline", "offline", "destructive"}

    def test_test_results(self):
        assert TEST_RESULTS == {"pass", "fail"}

    def test_nc_types(self):
        assert NC_TYPES == {"defect", "out_of_spec", "other"}

    def test_dispositions(self):
        assert DISPOSITIONS == {"rework", "scrap", "use_as_is", "return"}


# ═══════════════════════════════════════════════════════════════════
# Event Tests
# ═══════════════════════════════════════════════════════════════════


class TestQualityEvents:
    def test_test_passed(self):
        ev = quality_test_passed("t1", "u1", "r1")
        assert ev.event_type == "quality.test.passed"
        assert ev.payload["test_id"] == "t1"
        assert ev.payload["result_id"] == "r1"

    def test_test_failed(self):
        ev = quality_test_failed("t2", None, "r2")
        assert ev.event_type == "quality.test.failed"
        assert ev.payload["unit_id"] is None

    def test_nc_created(self):
        ev = quality_nc_created("nc1", "u1", "defect")
        assert ev.event_type == "quality.nc.created"
        assert ev.payload["nc_type"] == "defect"

    def test_nc_resolved(self):
        ev = quality_nc_resolved("nc1", "rework")
        assert ev.event_type == "quality.nc.resolved"
        assert ev.payload["disposition"] == "rework"


# ═══════════════════════════════════════════════════════════════════
# Exception Tests
# ═══════════════════════════════════════════════════════════════════


class TestQualityExceptions:
    def test_duplicate_test_code(self):
        exc = DuplicateTestCodeException("TST-1")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_TEST_CODE"
        assert "TST-1" in str(exc)
        assert exc.details["test_code"] == "TST-1"

    def test_invalid_nc_transition(self):
        exc = InvalidNCTransitionException("open", "closed")
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_NC_TRANSITION"
        assert exc.details["current_status"] == "open"
        assert exc.details["requested_status"] == "closed"

    def test_disposition_required(self):
        exc = DispositionRequiredException()
        assert exc.status_code == 422
        assert exc.error_code == "DISPOSITION_REQUIRED"


# ═══════════════════════════════════════════════════════════════════
# Service / Route Import Tests
# ═══════════════════════════════════════════════════════════════════


class TestServiceAndRouteImports:
    def test_quality_test_service_methods(self):
        from mes.core.quality.service import QualityTestService
        assert hasattr(QualityTestService, "list_tests")
        assert hasattr(QualityTestService, "get_test")
        assert hasattr(QualityTestService, "create_test")
        assert hasattr(QualityTestService, "update_test")

    def test_test_result_service_methods(self):
        from mes.core.quality.service import TestResultService
        assert hasattr(TestResultService, "record_result")
        assert hasattr(TestResultService, "get_result")
        assert hasattr(TestResultService, "list_results")

    def test_nc_service_methods(self):
        from mes.core.quality.service import NonConformanceService
        assert hasattr(NonConformanceService, "create_nc")
        assert hasattr(NonConformanceService, "get_nc")
        assert hasattr(NonConformanceService, "list_ncs")
        assert hasattr(NonConformanceService, "update_nc")

    def test_router_paths(self):
        from mes.core.quality.routes import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/quality/tests" in paths
        assert "/api/v1/quality/tests/{test_id}" in paths
        assert "/api/v1/quality/results" in paths
        assert "/api/v1/quality/results/{result_id}" in paths
        assert "/api/v1/quality/non-conformances" in paths
        assert "/api/v1/quality/non-conformances/{nc_id}" in paths
