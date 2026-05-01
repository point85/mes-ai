"""
Unit tests for the ROUTE-ENGINE (Routing Engine) module.

NOTE: This file was reduced as part of the routing-graph refactor that
replaced the predefined transition table (``ProcessSegmentDependency``)
with per-step input/output disposition lists
(``ProcessSegmentInputDisposition`` / ``ProcessSegmentOutputDisposition``).
The legacy `StepTransition*` model/schema/graph-routing tests were removed.
A new test module covering the disposition-list routing engine should be
added in a follow-up.

Surviving covered areas:
- Pure step-ordering logic (sort by sequence, skip inactive, etc.)
- Route active/default flags
- MoveRequest schema (still uses result + disposition fields)
"""

from __future__ import annotations

import types
import uuid

import pytest

# Bootstrap SQLAlchemy mappers — needed when importing services that touch
# cross-module relationships.
import mes.framework.auth.models  # noqa: F401
import mes.framework.plugin.models  # noqa: F401
import mes.core.physical_model.models  # noqa: F401
import mes.core.product_def.models  # noqa: F401
import mes.core.uom.models  # noqa: F401
import mes.core.operations.models  # noqa: F401
import mes.core.wip.models  # noqa: F401
import mes.core.material.models  # noqa: F401
import mes.core.data_collection.models  # noqa: F401
import mes.core.quality.models  # noqa: F401
import mes.core.performance.models  # noqa: F401


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_step(sequence: int, **overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "route_id": uuid.uuid4(),
        "sequence": sequence,
        "name": f"Step {sequence}",
        "step_type": "production",
        "is_active": True,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_route(steps: list | None = None, **overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "name": "Test Route",
        "version": "1.0",
        "is_default": True,
        "is_active": True,
        "steps": steps or [],
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═════════════════════════════════════════════════════════════════════
# STEP ORDERING TESTS (pure logic, no DB)
# ═════════════════════════════════════════════════════════════════════


class TestStepOrdering:
    def test_steps_sorted_by_sequence(self):
        s30 = _make_step(30)
        s10 = _make_step(10)
        s20 = _make_step(20)
        steps = sorted([s30, s10, s20], key=lambda s: s.sequence)
        assert [s.sequence for s in steps] == [10, 20, 30]

    def test_first_active_step(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        s5_inactive = _make_step(5, is_active=False)
        steps = sorted([s20, s5_inactive, s10], key=lambda s: s.sequence)
        active = [s for s in steps if s.is_active]
        assert active[0].sequence == 10

    def test_skip_inactive_steps(self):
        s10 = _make_step(10)
        s20 = _make_step(20, is_active=False)
        s30 = _make_step(30)
        all_steps = sorted([s10, s20, s30], key=lambda s: s.sequence)
        active = [s for s in all_steps if s.is_active]
        assert [s.sequence for s in active] == [10, 30]


class TestRouteResolution:
    def test_route_with_steps(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        route = _make_route(steps=[s10, s20])
        assert len(route.steps) == 2

    def test_default_route_flag(self):
        assert _make_route(is_default=True).is_default is True
        assert _make_route(is_default=False).is_default is False

    def test_route_active_flag(self):
        assert _make_route(is_active=True).is_active is True
        assert _make_route(is_active=False).is_active is False


class TestStepSequenceConvention:
    def test_insert_between_steps(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        s30 = _make_step(30)
        s15 = _make_step(15)
        steps = sorted([s10, s20, s30, s15], key=lambda s: s.sequence)
        assert [s.sequence for s in steps] == [10, 15, 20, 30]

    def test_resequenced_steps(self):
        s1 = _make_step(1)
        s100 = _make_step(100)
        s50 = _make_step(50)
        steps = sorted([s100, s1, s50], key=lambda s: s.sequence)
        assert [s.sequence for s in steps] == [1, 50, 100]


# ═════════════════════════════════════════════════════════════════════
# MoveRequest schema (still relevant under the new disposition model)
# ═════════════════════════════════════════════════════════════════════


class TestMoveRequestSchemas:
    def test_move_request_minimal(self):
        from mes.core.wip.schemas import MoveRequest
        m = MoveRequest()
        assert m.target_step_id is None
        assert m.result is None
        assert m.disposition is None

    def test_move_request_with_result(self):
        from mes.core.wip.schemas import MoveRequest
        m = MoveRequest(result="fail")
        assert m.result == "fail"

    def test_move_request_with_disposition(self):
        from mes.core.wip.schemas import MoveRequest
        m = MoveRequest(disposition="Return to rework")
        assert m.disposition == "Return to rework"

    def test_move_request_invalid_result_rejected(self):
        from pydantic import ValidationError
        from mes.core.wip.schemas import MoveRequest
        with pytest.raises(ValidationError, match="result"):
            MoveRequest(result="invalid_result")

    @pytest.mark.parametrize("result", ["pass", "fail", "rework"])
    def test_move_request_valid_results(self, result):
        from mes.core.wip.schemas import MoveRequest
        m = MoveRequest(result=result)
        assert m.result == result

    def test_move_request_with_target_and_result(self):
        from mes.core.wip.schemas import MoveRequest
        tid = uuid.uuid4()
        m = MoveRequest(target_step_id=tid, result="pass")
        assert m.target_step_id == tid
        assert m.result == "pass"


# ═════════════════════════════════════════════════════════════════════
# Disposition-list models (replacement for the old StepTransition tests)
# ═════════════════════════════════════════════════════════════════════


class TestDispositionListModels:
    def test_input_disposition_tablename(self):
        from mes.core.product_def.models import ProcessSegmentInputDisposition
        assert (
            ProcessSegmentInputDisposition.__tablename__
            == "process_segment_input_dispositions"
        )

    def test_output_disposition_tablename(self):
        from mes.core.product_def.models import ProcessSegmentOutputDisposition
        assert (
            ProcessSegmentOutputDisposition.__tablename__
            == "process_segment_output_dispositions"
        )

    def test_input_disposition_columns(self):
        from mes.core.product_def.models import ProcessSegmentInputDisposition
        cols = {c.key for c in ProcessSegmentInputDisposition.__mapper__.columns}
        assert {"step_id", "disposition_id", "position"}.issubset(cols)

    def test_output_disposition_columns(self):
        from mes.core.product_def.models import ProcessSegmentOutputDisposition
        cols = {c.key for c in ProcessSegmentOutputDisposition.__mapper__.columns}
        assert {"step_id", "disposition_id", "position"}.issubset(cols)

    def test_route_step_has_disposition_list_relationships(self):
        from mes.core.product_def.models import ProcessSegment
        rels = {r.key for r in ProcessSegment.__mapper__.relationships}
        assert "input_dispositions" in rels
        assert "output_dispositions" in rels

    def test_route_step_has_is_initial_step_column(self):
        from mes.core.product_def.models import ProcessSegment
        cols = {c.key for c in ProcessSegment.__mapper__.columns}
        assert "is_initial_step" in cols
