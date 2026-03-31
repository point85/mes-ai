"""
Unit tests for REASON-CODES feature.

Covers:
- Reason model table, columns, repr
- ReasonCreate / ReasonUpdate / ReasonRead / ManualTransitionRequest schemas
- ReasonService import and method signatures
- Reason-specific router paths
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.performance.models import Reason
from mes.core.performance.schemas import (
    OEE_BUCKETS,
    ManualTransitionRequest,
    ReasonCreate,
    ReasonRead,
    ReasonUpdate,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_reason(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "code": "1000",
        "name": "Electrical",
        "description": "Electrical failures",
        "oee_bucket": "downtime_unplanned",
        "parent_id": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═══════════════════════════════════════════════════════════════════
# Model Tests
# ═══════════════════════════════════════════════════════════════════


class TestReasonModel:
    def test_tablename(self):
        assert Reason.__tablename__ == "reasons"

    def test_mapper_columns(self):
        cols = {c.key for c in Reason.__table__.columns}
        assert "code" in cols
        assert "name" in cols
        assert "description" in cols
        assert "oee_bucket" in cols
        assert "parent_id" in cols

    def test_base_model_columns(self):
        cols = {c.key for c in Reason.__table__.columns}
        assert "id" in cols
        assert "is_active" in cols
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_repr(self):
        r = Reason()
        r.id = uuid.uuid4()
        r.code = "1000"
        r.name = "Electrical"
        text = repr(r)
        assert "1000" in text
        assert "Electrical" in text


# ═══════════════════════════════════════════════════════════════════
# ReasonCreate Schema Tests
# ═══════════════════════════════════════════════════════════════════


class TestReasonCreateSchema:
    def test_valid_minimal(self):
        schema = ReasonCreate(
            code="1000",
            name="Electrical",
            oee_bucket="downtime_unplanned",
            parent_id=None,
        )
        assert schema.code == "1000"
        assert schema.parent_id is None
        assert schema.description is None

    def test_valid_full(self):
        parent_id = uuid.uuid4()
        schema = ReasonCreate(
            code="1010",
            name="AC Motors",
            description="AC motor failures",
            oee_bucket="downtime_unplanned",
            parent_id=parent_id,
        )
        assert schema.parent_id == parent_id
        assert schema.description == "AC motor failures"

    def test_code_too_short(self):
        with pytest.raises(ValidationError, match="code"):
            ReasonCreate(
                code="10",
                name="Bad",
                oee_bucket="downtime_unplanned",
                parent_id=None,
            )

    def test_code_too_long(self):
        with pytest.raises(ValidationError, match="code"):
            ReasonCreate(
                code="12345",
                name="Bad",
                oee_bucket="downtime_unplanned",
                parent_id=None,
            )

    def test_empty_name_fails(self):
        with pytest.raises(ValidationError, match="name"):
            ReasonCreate(
                code="1000",
                name="",
                oee_bucket="downtime_unplanned",
                parent_id=None,
            )

    def test_invalid_oee_bucket_fails(self):
        with pytest.raises(ValidationError, match="oee_bucket"):
            ReasonCreate(
                code="1000",
                name="Electrical",
                oee_bucket="invalid_bucket",
                parent_id=None,
            )

    def test_all_oee_buckets_accepted(self):
        for bucket in OEE_BUCKETS:
            schema = ReasonCreate(
                code="1000", name="Test", oee_bucket=bucket, parent_id=None,
            )
            assert schema.oee_bucket == bucket


# ═══════════════════════════════════════════════════════════════════
# ReasonUpdate Schema Tests
# ═══════════════════════════════════════════════════════════════════


class TestReasonUpdateSchema:
    def test_empty_update(self):
        schema = ReasonUpdate()  # type: ignore[call-arg]  # Pylance vs __future__.annotations + Field(None)
        assert schema.name is None
        assert schema.oee_bucket is None
        assert schema.parent_id is None

    def test_partial_update(self):
        schema = ReasonUpdate(name="Updated Name")  # type: ignore[call-arg]
        assert schema.name == "Updated Name"
        assert schema.oee_bucket is None

    def test_oee_bucket_update(self):
        schema = ReasonUpdate(oee_bucket="downtime_planned")  # type: ignore[call-arg]
        assert schema.oee_bucket == "downtime_planned"

    def test_invalid_oee_bucket_fails(self):
        with pytest.raises(ValidationError, match="oee_bucket"):
            ReasonUpdate(oee_bucket="invalid_bucket")  # type: ignore[call-arg]


# ═══════════════════════════════════════════════════════════════════
# ReasonRead Schema Tests
# ═══════════════════════════════════════════════════════════════════


class TestReasonReadSchema:
    def test_from_attributes(self):
        obj = _make_reason()
        schema = ReasonRead.model_validate(obj, from_attributes=True)
        assert schema.code == "1000"
        assert schema.name == "Electrical"
        assert schema.oee_bucket == "downtime_unplanned"
        assert schema.parent_id is None
        assert schema.is_active is True

    def test_with_parent(self):
        parent_id = uuid.uuid4()
        obj = _make_reason(parent_id=parent_id)
        schema = ReasonRead.model_validate(obj, from_attributes=True)
        assert schema.parent_id == parent_id

    def test_all_fields_present(self):
        obj = _make_reason()
        schema = ReasonRead.model_validate(obj, from_attributes=True)
        assert schema.id is not None
        assert schema.created_at is not None
        assert schema.updated_at is not None


# ═══════════════════════════════════════════════════════════════════
# ManualTransitionRequest Schema Tests
# ═══════════════════════════════════════════════════════════════════


class TestManualTransitionRequestSchema:
    def test_valid_request(self):
        reason_id = uuid.uuid4()
        schema = ManualTransitionRequest(reason_id=reason_id)
        assert schema.reason_id == reason_id
        assert schema.notes is None

    def test_with_notes(self):
        schema = ManualTransitionRequest(
            reason_id=uuid.uuid4(),
            notes="Operator-initiated downtime",
        )
        assert schema.notes == "Operator-initiated downtime"

    def test_missing_reason_id_fails(self):
        with pytest.raises(ValidationError, match="reason_id"):
            ManualTransitionRequest()  # type: ignore[call-arg]  # intentional: testing validation


# ═══════════════════════════════════════════════════════════════════
# Service Import Tests
# ═══════════════════════════════════════════════════════════════════


class TestReasonServiceImports:
    def test_reason_service_exists(self):
        from mes.core.performance.service import ReasonService
        assert ReasonService is not None

    def test_service_methods(self):
        from mes.core.performance.service import ReasonService
        assert hasattr(ReasonService, "create_reason")
        assert hasattr(ReasonService, "list_reasons")
        assert hasattr(ReasonService, "get_reason")
        assert hasattr(ReasonService, "update_reason")
        assert hasattr(ReasonService, "delete_reason")


# ═══════════════════════════════════════════════════════════════════
# Router Path Tests
# ═══════════════════════════════════════════════════════════════════


class TestReasonRouterPaths:
    def test_reason_crud_paths(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/api/v1/performance/reasons" in paths
        assert "/api/v1/performance/reasons/{reason_id}" in paths

    def test_manual_transition_path(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/api/v1/performance/equipment/{equip_id}/manual-transition" in paths
