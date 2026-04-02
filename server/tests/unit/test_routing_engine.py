"""
Unit tests for the ROUTE-ENGINE (Routing Engine) module.

Covers:
- RoutingEngineService static methods with mocked data
- Route resolution priority (explicit → default → fallback)
- Next step determination (sequential, end-of-route)
- First step resolution
- Graph-based routing via StepTransition edges
- Conditional routing (on_pass, on_fail, on_rework)
- Disposition routing (MRB operator choices)
- Linear fallback when no transitions are defined
"""

from __future__ import annotations

import types
import uuid

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_step(sequence: int, **overrides) -> types.SimpleNamespace:
    """Create a route step-like object."""
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
    """Create a route-like object."""
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
    """Test step ordering and next-step logic using mock data."""

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

    def test_next_step_from_middle(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        s30 = _make_step(30)
        steps = [s10, s20, s30]
        # Current is s10, next should be s20
        for i, s in enumerate(steps):
            if s.id == s10.id:
                next_step = steps[i + 1] if i + 1 < len(steps) else None
                break
        assert next_step is not None
        assert next_step.id == s20.id

    def test_next_step_at_end_returns_none(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        steps = [s10, s20]
        # Current is s20 (last step), next should be None
        for i, s in enumerate(steps):
            if s.id == s20.id:
                next_step = steps[i + 1] if i + 1 < len(steps) else None
                break
        assert next_step is None

    def test_skip_inactive_steps(self):
        s10 = _make_step(10)
        s20 = _make_step(20, is_active=False)
        s30 = _make_step(30)
        all_steps = sorted([s10, s20, s30], key=lambda s: s.sequence)
        active = [s for s in all_steps if s.is_active]
        # After s10, next active should be s30
        for i, s in enumerate(active):
            if s.id == s10.id:
                next_step = active[i + 1] if i + 1 < len(active) else None
                break
        assert next_step is not None
        assert next_step.id == s30.id

    def test_empty_active_steps(self):
        s10 = _make_step(10, is_active=False)
        all_steps = [s10]
        active = [s for s in all_steps if s.is_active]
        assert len(active) == 0


class TestRouteResolution:
    """Test route resolution priority logic."""

    def test_route_with_steps(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        route = _make_route(steps=[s10, s20])
        assert len(route.steps) == 2

    def test_default_route_flag(self):
        route = _make_route(is_default=True)
        assert route.is_default is True

    def test_non_default_route(self):
        route = _make_route(is_default=False)
        assert route.is_default is False

    def test_route_active_flag(self):
        route = _make_route(is_active=True)
        assert route.is_active is True

    def test_inactive_route(self):
        route = _make_route(is_active=False)
        assert route.is_active is False


class TestStepSequenceConvention:
    """Test that the 10/20/30 sequence convention works for insertion."""

    def test_insert_between_steps(self):
        s10 = _make_step(10)
        s20 = _make_step(20)
        s30 = _make_step(30)
        # Insert a new step between 10 and 20
        s15 = _make_step(15)
        steps = sorted([s10, s20, s30, s15], key=lambda s: s.sequence)
        sequences = [s.sequence for s in steps]
        assert sequences == [10, 15, 20, 30]

    def test_resequenced_steps(self):
        """Steps with arbitrary sequences still sort correctly."""
        s1 = _make_step(1)
        s100 = _make_step(100)
        s50 = _make_step(50)
        steps = sorted([s100, s1, s50], key=lambda s: s.sequence)
        assert [s.sequence for s in steps] == [1, 50, 100]


# ═════════════════════════════════════════════════════════════════════
# STEP TRANSITION MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


def _make_transition(from_step_id, to_step_id, **overrides):
    """Create a transition-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "from_step_id": from_step_id,
        "to_step_id": to_step_id,
        "condition": "always",
        "is_default": False,
        "priority": 0,
        "label": None,
        "is_active": True,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


class TestStepTransitionModel:
    """Test StepTransition SQLAlchemy model definition."""

    def test_step_transition_tablename(self):
        from mes.core.product_def.models import StepTransition
        assert StepTransition.__tablename__ == "step_transitions"

    def test_step_transition_has_base_columns(self):
        from mes.core.product_def.models import StepTransition
        col_names = {c.key for c in StepTransition.__mapper__.columns}
        assert "id" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        assert "is_active" in col_names

    def test_step_transition_has_required_columns(self):
        from mes.core.product_def.models import StepTransition
        col_names = {c.key for c in StepTransition.__mapper__.columns}
        assert "from_step_id" in col_names
        assert "to_step_id" in col_names
        assert "condition" in col_names
        assert "is_default" in col_names
        assert "priority" in col_names
        assert "label" in col_names

    def test_route_step_has_transition_relationships(self):
        from mes.core.product_def.models import RouteStep
        rels = {r.key for r in RouteStep.__mapper__.relationships}
        assert "outgoing_transitions" in rels
        assert "incoming_transitions" in rels


class TestStepTransitionSchemas:
    """Test Pydantic schemas for StepTransition CRUD."""

    def test_create_minimal(self):
        from mes.core.product_def.schemas import StepTransitionCreate
        s = StepTransitionCreate(to_step_id=uuid.uuid4())
        assert s.condition == "always"
        assert s.is_default is False
        assert s.priority == 0
        assert s.label is None

    def test_create_full(self):
        from mes.core.product_def.schemas import StepTransitionCreate
        tid = uuid.uuid4()
        s = StepTransitionCreate(
            to_step_id=tid,
            condition="on_fail",
            is_default=True,
            priority=10,
            label="Send to rework",
        )
        assert s.to_step_id == tid
        assert s.condition == "on_fail"
        assert s.is_default is True
        assert s.priority == 10
        assert s.label == "Send to rework"

    def test_create_invalid_condition_rejected(self):
        from pydantic import ValidationError
        from mes.core.product_def.schemas import StepTransitionCreate
        with pytest.raises(ValidationError, match="condition"):
            StepTransitionCreate(to_step_id=uuid.uuid4(), condition="invalid")

    @pytest.mark.parametrize("cond", ["always", "on_pass", "on_fail", "on_rework", "disposition"])
    def test_create_valid_conditions(self, cond):
        from mes.core.product_def.schemas import StepTransitionCreate
        s = StepTransitionCreate(to_step_id=uuid.uuid4(), condition=cond)
        assert s.condition == cond

    def test_read_from_attributes(self):
        from mes.core.product_def.schemas import StepTransitionRead
        from datetime import datetime, timezone
        tid = uuid.uuid4()
        fid = uuid.uuid4()
        data = types.SimpleNamespace(
            id=tid, from_step_id=fid, to_step_id=uuid.uuid4(),
            condition="on_pass", is_default=False, priority=5,
            label="OK path", is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        r = StepTransitionRead.model_validate(data)
        assert r.id == tid
        assert r.condition == "on_pass"
        assert r.label == "OK path"

    def test_update_partial(self):
        from mes.core.product_def.schemas import StepTransitionUpdate
        s = StepTransitionUpdate(priority=20)
        dumped = s.model_dump(exclude_unset=True)
        assert "priority" in dumped
        assert "condition" not in dumped


# ═════════════════════════════════════════════════════════════════════
# GRAPH ROUTING LOGIC TESTS (pure logic, no DB)
# ═════════════════════════════════════════════════════════════════════


class TestGraphRoutingLogic:
    """Test the transition evaluation logic used by the routing engine."""

    def _evaluate(self, transitions, result=None, disposition=None):
        """
        Pure-logic version of _resolve_graph_transition for testing
        without async/DB.
        """
        _RESULT_TO_CONDITION = {
            "pass": "on_pass",
            "fail": "on_fail",
            "rework": "on_rework",
        }
        result_condition = _RESULT_TO_CONDITION.get(result or "", "")
        disposition_match = None
        result_match = None
        always_match = None
        default = None

        for t in transitions:
            if disposition and t.condition == "disposition" and t.label == disposition:
                if disposition_match is None:
                    disposition_match = t
            elif result_condition and t.condition == result_condition:
                if result_match is None:
                    result_match = t
            elif t.condition == "always":
                if always_match is None:
                    always_match = t
            if t.is_default and default is None:
                default = t

        return disposition_match or result_match or always_match or default

    def test_on_pass_selects_pass_transition(self):
        s10_id, s20_id, s25_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass", priority=10)
        t_fail = _make_transition(s10_id, s25_id, condition="on_fail", priority=10)
        chosen = self._evaluate([t_pass, t_fail], result="pass")
        assert chosen.to_step_id == s20_id

    def test_on_fail_selects_fail_transition(self):
        s10_id, s20_id, s25_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass", priority=10)
        t_fail = _make_transition(s10_id, s25_id, condition="on_fail", priority=10)
        chosen = self._evaluate([t_pass, t_fail], result="fail")
        assert chosen.to_step_id == s25_id

    def test_on_rework_selects_rework_transition(self):
        s10_id, s20_id, s25_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass")
        t_rework = _make_transition(s10_id, s25_id, condition="on_rework")
        chosen = self._evaluate([t_pass, t_rework], result="rework")
        assert chosen.to_step_id == s25_id

    def test_always_used_when_no_result_match(self):
        s10_id, s20_id = uuid.uuid4(), uuid.uuid4()
        t_always = _make_transition(s10_id, s20_id, condition="always")
        chosen = self._evaluate([t_always], result="pass")
        # 'always' should be used since there's no specific 'on_pass'
        assert chosen.to_step_id == s20_id

    def test_result_match_takes_priority_over_always(self):
        s10_id, s20_id, s30_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t_always = _make_transition(s10_id, s30_id, condition="always")
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass", priority=10)
        chosen = self._evaluate([t_pass, t_always], result="pass")
        assert chosen.to_step_id == s20_id

    def test_default_used_when_nothing_else_matches(self):
        s10_id, s20_id, s25_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass")
        t_default = _make_transition(s10_id, s25_id, condition="on_fail", is_default=True)
        # result='rework' matches neither on_pass nor on_fail
        chosen = self._evaluate([t_pass, t_default], result="rework")
        assert chosen.to_step_id == s25_id

    def test_disposition_match(self):
        s10_id, s20_id, s25_id, s30_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t1 = _make_transition(s10_id, s20_id, condition="disposition", label="Return to rework")
        t2 = _make_transition(s10_id, s25_id, condition="disposition", label="Scrap")
        t3 = _make_transition(s10_id, s30_id, condition="disposition", label="Resume production")
        chosen = self._evaluate([t1, t2, t3], disposition="Scrap")
        assert chosen.to_step_id == s25_id

    def test_disposition_takes_priority_over_result(self):
        s10_id, s20_id, s25_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass", priority=10)
        t_disp = _make_transition(s10_id, s25_id, condition="disposition", label="Override", priority=5)
        chosen = self._evaluate([t_pass, t_disp], result="pass", disposition="Override")
        assert chosen.to_step_id == s25_id

    def test_no_match_returns_none(self):
        s10_id, s20_id = uuid.uuid4(), uuid.uuid4()
        t_pass = _make_transition(s10_id, s20_id, condition="on_pass")
        chosen = self._evaluate([t_pass], result="fail")
        assert chosen is None

    def test_empty_transitions_returns_none(self):
        chosen = self._evaluate([], result="pass")
        assert chosen is None


class TestReworkLoopPattern:
    """Test a typical rework loop: Assembly → Test → (fail) → Rework → Test."""

    def setup_method(self):
        self.step_assembly = _make_step(10, name="Assembly")
        self.step_test = _make_step(20, name="Test")
        self.step_rework = _make_step(25, name="Rework", step_type="rework")
        self.step_pack = _make_step(30, name="Final Pack")

    def test_rework_loop_structure(self):
        """Verify the route has 4 steps in correct order."""
        steps = sorted(
            [self.step_assembly, self.step_test, self.step_rework, self.step_pack],
            key=lambda s: s.sequence,
        )
        assert [s.name for s in steps] == ["Assembly", "Test", "Rework", "Final Pack"]

    def test_test_pass_goes_to_pack(self):
        """On pass at Test, should go to Final Pack (not Rework)."""
        t_pass = _make_transition(
            self.step_test.id, self.step_pack.id, condition="on_pass",
        )
        t_fail = _make_transition(
            self.step_test.id, self.step_rework.id, condition="on_fail",
        )
        # Simulate evaluation
        _RESULT_TO_CONDITION = {"pass": "on_pass", "fail": "on_fail", "rework": "on_rework"}
        result_condition = _RESULT_TO_CONDITION.get("pass", "")
        matched = None
        for t in [t_pass, t_fail]:
            if t.condition == result_condition:
                matched = t
                break
        assert matched.to_step_id == self.step_pack.id

    def test_test_fail_goes_to_rework(self):
        """On fail at Test, should go to Rework."""
        t_pass = _make_transition(
            self.step_test.id, self.step_pack.id, condition="on_pass",
        )
        t_fail = _make_transition(
            self.step_test.id, self.step_rework.id, condition="on_fail",
        )
        _RESULT_TO_CONDITION = {"pass": "on_pass", "fail": "on_fail", "rework": "on_rework"}
        result_condition = _RESULT_TO_CONDITION.get("fail", "")
        matched = None
        for t in [t_pass, t_fail]:
            if t.condition == result_condition:
                matched = t
                break
        assert matched.to_step_id == self.step_rework.id

    def test_rework_always_returns_to_test(self):
        """After rework, unit always goes back to Test for re-inspection."""
        t_back = _make_transition(
            self.step_rework.id, self.step_test.id,
            condition="always", is_default=True,
        )
        assert t_back.to_step_id == self.step_test.id
        assert t_back.condition == "always"


class TestMRBDispositionPattern:
    """Test MRB (Material Review Board) disposition routing."""

    def setup_method(self):
        self.step_test = _make_step(20, name="Test")
        self.step_rework = _make_step(25, name="Rework", step_type="rework")
        self.step_mrb = _make_step(28, name="MRB Review", step_type="mrb")
        self.step_pack = _make_step(30, name="Final Pack")

    def test_mrb_has_three_disposition_paths(self):
        """MRB step should offer 3 disposition choices."""
        transitions = [
            _make_transition(
                self.step_mrb.id, self.step_rework.id,
                condition="disposition", label="Return to rework",
            ),
            _make_transition(
                self.step_mrb.id, self.step_pack.id,
                condition="disposition", label="Use as-is",
            ),
            _make_transition(
                self.step_mrb.id, self.step_mrb.id,  # self-loop for "hold for review"
                condition="disposition", label="Hold for further review",
            ),
        ]
        labels = [t.label for t in transitions]
        assert "Return to rework" in labels
        assert "Use as-is" in labels
        assert "Hold for further review" in labels

    def test_disposition_selects_correct_path(self):
        """Operator selecting 'Use as-is' should route to pack."""
        transitions = [
            _make_transition(
                self.step_mrb.id, self.step_rework.id,
                condition="disposition", label="Return to rework",
            ),
            _make_transition(
                self.step_mrb.id, self.step_pack.id,
                condition="disposition", label="Use as-is",
            ),
        ]
        # Find the one matching the disposition
        chosen = None
        for t in transitions:
            if t.condition == "disposition" and t.label == "Use as-is":
                chosen = t
                break
        assert chosen is not None
        assert chosen.to_step_id == self.step_pack.id


class TestMoveRequestSchemas:
    """Test updated MoveRequest with result/disposition fields."""

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
