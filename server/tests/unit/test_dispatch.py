"""
Unit tests for DISPATCH (Dispatching Engine) module.

Covers:
- Schema validation for dispatch requests, responses, strategies, queue
- Event factory functions (including blocked, starved)
- Exception construction (including capacity, material capability)
- Strategy logic (_apply_strategy)
- Service / route imports
- Constants validation
- EquipmentDispatchStatus schema
- Blocked/starved response fields
- Handler registration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.dispatch.events import (
    dispatch_blocked,
    dispatch_evaluated,
    dispatch_executed,
    equipment_starved,
)
from mes.core.dispatch.exceptions import (
    EquipmentAtCapacityException,
    InvalidDispatchTargetException,
    MaterialCapabilityException,
    NoEligibleEquipmentException,
    NoRouteForDispatchException,
)
from mes.core.dispatch.schemas import (
    DISPATCH_STRATEGIES,
    DispatchEvaluateRequest,
    DispatchEvaluateResponse,
    DispatchExecuteRequest,
    DispatchExecuteResponse,
    DispatchOption,
    DispatchQueueItem,
    DispatchStrategyInfo,
    EquipmentDispatchStatus,
)
from mes.core.dispatch.service import (
    STRATEGY_DESCRIPTIONS,
    DispatchService,
    _apply_strategy,
)


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — Dispatch Evaluate
# ═══════════════════════════════════════════════════════════════════


class TestDispatchEvaluateRequest:
    def test_defaults(self):
        schema = DispatchEvaluateRequest(unit_id=uuid.uuid4())
        assert schema.strategy == "first_available"
        assert schema.lot_id is None

    def test_all_strategies_valid(self):
        for s in DISPATCH_STRATEGIES:
            schema = DispatchEvaluateRequest(unit_id=uuid.uuid4(), strategy=s)
            assert schema.strategy == s

    def test_invalid_strategy(self):
        with pytest.raises(ValidationError, match="strategy"):
            DispatchEvaluateRequest(unit_id=uuid.uuid4(), strategy="invalid")

    def test_with_lot(self):
        lid = uuid.uuid4()
        schema = DispatchEvaluateRequest(lot_id=lid, strategy="shortest_queue")
        assert schema.lot_id == lid
        assert schema.unit_id is None


class TestDispatchOption:
    def test_construction(self):
        opt = DispatchOption(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="CNC Mill",
            work_cell_id=uuid.uuid4(),
            work_cell_code="WC-001",
            step_id=uuid.uuid4(),
            step_name="Machining",
            queue_depth=3,
            score=0.85,
            reason="shortest queue",
        )
        assert opt.equipment_code == "EQ-001"
        assert opt.queue_depth == 3
        assert opt.score == 0.85

    def test_defaults(self):
        opt = DispatchOption(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-1",
            equipment_name="Equip",
            work_cell_id=uuid.uuid4(),
            work_cell_code="WC-1",
            step_id=uuid.uuid4(),
        )
        assert opt.queue_depth == 0
        assert opt.score == 0.0
        assert opt.reason is None


class TestDispatchEvaluateResponse:
    def test_empty_response(self):
        resp = DispatchEvaluateResponse(
            unit_id=uuid.uuid4(), strategy="first_available",
        )
        assert resp.options == []
        assert resp.recommended is None

    def test_with_options(self):
        opt = DispatchOption(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-1",
            equipment_name="Mill",
            work_cell_id=uuid.uuid4(),
            work_cell_code="WC-1",
            step_id=uuid.uuid4(),
        )
        resp = DispatchEvaluateResponse(
            unit_id=uuid.uuid4(),
            strategy="first_available",
            options=[opt],
            recommended=opt,
        )
        assert len(resp.options) == 1
        assert resp.recommended is not None


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — Dispatch Execute
# ═══════════════════════════════════════════════════════════════════


class TestDispatchExecuteSchemas:
    def test_request(self):
        schema = DispatchExecuteRequest(
            unit_id=uuid.uuid4(),
            destination_equipment_id=uuid.uuid4(),
            destination_step_id=uuid.uuid4(),
        )
        assert schema.lot_id is None

    def test_response(self):
        now = datetime.now(timezone.utc)
        resp = DispatchExecuteResponse(
            unit_id=uuid.uuid4(),
            destination_equipment_id=uuid.uuid4(),
            destination_step_id=uuid.uuid4(),
            dispatched_at=now,
        )
        assert resp.dispatched_at == now


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — Strategy / Queue
# ═══════════════════════════════════════════════════════════════════


class TestDispatchStrategyInfo:
    def test_construction(self):
        info = DispatchStrategyInfo(
            name="first_available",
            description="Route to first available",
        )
        assert info.strategy_type == "built-in"

    def test_custom_type(self):
        info = DispatchStrategyInfo(
            name="custom_logic",
            description="Custom plugin strategy",
            strategy_type="plugin",
        )
        assert info.strategy_type == "plugin"


class TestDispatchQueueItem:
    def test_unit_item(self):
        item = DispatchQueueItem(
            unit_id=uuid.uuid4(),
            serial_number="SN-001",
            status="queued",
        )
        assert item.lot_id is None
        assert item.status == "queued"

    def test_lot_item(self):
        item = DispatchQueueItem(
            lot_id=uuid.uuid4(),
            lot_number="LOT-001",
            status="in_process",
        )
        assert item.unit_id is None
        assert item.lot_number == "LOT-001"


# ═══════════════════════════════════════════════════════════════════
# Strategy Tests
# ═══════════════════════════════════════════════════════════════════


def _make_options(queue_depths: list[int]) -> list[DispatchOption]:
    """Create test dispatch options with varying queue depths."""
    return [
        DispatchOption(
            equipment_id=uuid.uuid4(),
            equipment_code=f"EQ-{i}",
            equipment_name=f"Equipment {i}",
            work_cell_id=uuid.uuid4(),
            work_cell_code="WC-1",
            step_id=uuid.uuid4(),
            queue_depth=qd,
        )
        for i, qd in enumerate(queue_depths)
    ]


class TestApplyStrategy:
    def test_first_available_preserves_order(self):
        options = _make_options([3, 1, 5])
        ranked = _apply_strategy(options, "first_available")
        # Should preserve original order
        assert ranked[0].queue_depth == 3
        assert all(opt.reason == "first available" for opt in ranked)
        # Scores descending
        assert ranked[0].score > ranked[-1].score

    def test_shortest_queue_sorts_ascending(self):
        options = _make_options([5, 2, 8, 1])
        ranked = _apply_strategy(options, "shortest_queue")
        assert ranked[0].queue_depth == 1
        assert ranked[1].queue_depth == 2
        assert ranked[2].queue_depth == 5
        assert ranked[3].queue_depth == 8

    def test_round_robin_sorts_by_queue(self):
        options = _make_options([4, 1, 3])
        ranked = _apply_strategy(options, "round_robin")
        assert ranked[0].queue_depth == 1

    def test_capability_match_preserves_order(self):
        options = _make_options([2, 3])
        ranked = _apply_strategy(options, "capability_match")
        assert ranked[0].queue_depth == 2

    def test_manual_zero_scores(self):
        options = _make_options([1, 2])
        ranked = _apply_strategy(options, "manual")
        assert all(opt.score == 0.0 for opt in ranked)
        assert all(opt.reason == "manual selection" for opt in ranked)

    def test_empty_options(self):
        ranked = _apply_strategy([], "first_available")
        assert ranked == []

    def test_single_option(self):
        options = _make_options([0])
        ranked = _apply_strategy(options, "shortest_queue")
        assert len(ranked) == 1

    def test_unknown_strategy_passes_through(self):
        options = _make_options([1, 2])
        ranked = _apply_strategy(options, "unknown_future")
        assert len(ranked) == 2


# ═══════════════════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════════════════


class TestDispatchConstants:
    def test_strategies(self):
        expected = {"manual", "first_available", "shortest_queue", "round_robin", "capability_match"}
        assert DISPATCH_STRATEGIES == expected

    def test_strategy_descriptions_match(self):
        assert set(STRATEGY_DESCRIPTIONS.keys()) == DISPATCH_STRATEGIES

    def test_list_strategies(self):
        strategies = DispatchService.list_strategies()
        assert len(strategies) == len(DISPATCH_STRATEGIES)
        names = {s.name for s in strategies}
        assert names == DISPATCH_STRATEGIES


# ═══════════════════════════════════════════════════════════════════
# Event Tests
# ═══════════════════════════════════════════════════════════════════


class TestDispatchEvents:
    def test_dispatch_evaluated(self):
        ev = dispatch_evaluated("u1", "first_available", "eq-1")
        assert ev.event_type == "dispatch.evaluated"
        assert ev.payload["strategy"] == "first_available"
        assert ev.payload["recommendation"] == "eq-1"

    def test_dispatch_evaluated_no_recommendation(self):
        ev = dispatch_evaluated("u1", "manual", None)
        assert ev.payload["recommendation"] is None

    def test_dispatch_executed(self):
        ev = dispatch_executed("u1", "step-1")
        assert ev.event_type == "dispatch.executed"
        assert ev.payload["destination_step_id"] == "step-1"


# ═══════════════════════════════════════════════════════════════════
# Exception Tests
# ═══════════════════════════════════════════════════════════════════


class TestDispatchExceptions:
    def test_no_eligible_equipment(self):
        exc = NoEligibleEquipmentException("step-1")
        assert exc.status_code == 422
        assert exc.error_code == "NO_ELIGIBLE_EQUIPMENT"
        assert exc.details["step_id"] == "step-1"

    def test_no_eligible_equipment_no_step(self):
        exc = NoEligibleEquipmentException()
        assert exc.details["step_id"] is None

    def test_invalid_dispatch_target(self):
        exc = InvalidDispatchTargetException("eq-1", "not available")
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_DISPATCH_TARGET"
        assert "eq-1" in str(exc)
        assert exc.details["reason"] == "not available"

    def test_no_route_for_dispatch(self):
        exc = NoRouteForDispatchException("SN-001")
        assert exc.status_code == 422
        assert exc.error_code == "NO_ROUTE_FOR_DISPATCH"
        assert "SN-001" in str(exc)


# ═══════════════════════════════════════════════════════════════════
# Service / Route Import Tests
# ═══════════════════════════════════════════════════════════════════


class TestServiceAndRouteImports:
    def test_dispatch_service_methods(self):
        assert hasattr(DispatchService, "list_strategies")
        assert hasattr(DispatchService, "evaluate")
        assert hasattr(DispatchService, "execute")
        assert hasattr(DispatchService, "get_queue")
        assert hasattr(DispatchService, "auto_dispatch")
        assert hasattr(DispatchService, "get_equipment_status")

    def test_router_paths(self):
        from mes.core.dispatch.routes import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/dispatch/evaluate" in paths
        assert "/api/v1/dispatch/execute" in paths
        assert "/api/v1/dispatch/strategies" in paths
        assert "/api/v1/dispatch/queue/{work_cell_id}" in paths
        assert "/api/v1/dispatch/auto" in paths
        assert "/api/v1/dispatch/equipment/{equipment_id}/status" in paths


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — EquipmentDispatchStatus
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentDispatchStatus:
    def test_construction(self):
        status = EquipmentDispatchStatus(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="CNC Mill",
            dispatch_category="available",
            queue_depth=3,
            max_queue_depth=5,
        )
        assert status.equipment_code == "EQ-001"
        assert status.dispatch_category == "available"
        assert status.queue_depth == 3
        assert status.max_queue_depth == 5
        assert status.is_starved is False
        assert status.is_at_capacity is False

    def test_starved(self):
        status = EquipmentDispatchStatus(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="Mill",
            dispatch_category="available",
            queue_depth=0,
            is_starved=True,
        )
        assert status.is_starved is True

    def test_at_capacity(self):
        status = EquipmentDispatchStatus(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="Mill",
            dispatch_category="available",
            queue_depth=5,
            max_queue_depth=5,
            is_at_capacity=True,
        )
        assert status.is_at_capacity is True

    def test_unlimited_queue(self):
        status = EquipmentDispatchStatus(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="Mill",
            dispatch_category="available",
            queue_depth=100,
            max_queue_depth=None,
        )
        assert status.max_queue_depth is None
        assert status.is_at_capacity is False


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — Blocked Response
# ═══════════════════════════════════════════════════════════════════


class TestBlockedResponse:
    def test_blocked_evaluate_response(self):
        resp = DispatchEvaluateResponse(
            lot_id=uuid.uuid4(),
            strategy="shortest_queue",
            options=[],
            blocked=True,
            blocked_reason="EQ-001: queue full (5/5); EQ-002: unavailable (busy)",
        )
        assert resp.blocked is True
        assert "queue full" in resp.blocked_reason
        assert resp.options == []
        assert resp.recommended is None

    def test_not_blocked_by_default(self):
        resp = DispatchEvaluateResponse(
            unit_id=uuid.uuid4(),
            strategy="first_available",
        )
        assert resp.blocked is False
        assert resp.blocked_reason is None

    def test_blocked_no_reason(self):
        resp = DispatchEvaluateResponse(
            lot_id=uuid.uuid4(),
            strategy="first_available",
            blocked=True,
        )
        assert resp.blocked is True
        assert resp.blocked_reason is None


# ═══════════════════════════════════════════════════════════════════
# Schema Tests — DispatchOption with max_queue_depth
# ═══════════════════════════════════════════════════════════════════


class TestDispatchOptionCapacity:
    def test_max_queue_depth_included(self):
        opt = DispatchOption(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="Mill",
            work_cell_id=uuid.uuid4(),
            work_cell_code="WC-1",
            step_id=uuid.uuid4(),
            queue_depth=2,
            max_queue_depth=5,
        )
        assert opt.max_queue_depth == 5
        assert opt.queue_depth == 2

    def test_max_queue_depth_none_unlimited(self):
        opt = DispatchOption(
            equipment_id=uuid.uuid4(),
            equipment_code="EQ-001",
            equipment_name="Mill",
            work_cell_id=uuid.uuid4(),
            work_cell_code="WC-1",
            step_id=uuid.uuid4(),
        )
        assert opt.max_queue_depth is None


# ═══════════════════════════════════════════════════════════════════
# Event Tests — Blocked / Starved
# ═══════════════════════════════════════════════════════════════════


class TestBlockedStarvedEvents:
    def test_dispatch_blocked_lot(self):
        ev = dispatch_blocked(lot_id="lot-1", reason="queue full")
        assert ev.event_type == "dispatch.blocked"
        assert ev.source == "dispatch"
        assert ev.payload["lot_id"] == "lot-1"
        assert ev.payload["unit_id"] is None
        assert ev.payload["reason"] == "queue full"

    def test_dispatch_blocked_unit(self):
        ev = dispatch_blocked(unit_id="u-1", reason="not set up for material")
        assert ev.payload["unit_id"] == "u-1"
        assert ev.payload["lot_id"] is None

    def test_dispatch_blocked_no_reason(self):
        ev = dispatch_blocked()
        assert ev.payload["reason"] == ""

    def test_equipment_starved(self):
        ev = equipment_starved("eq-1")
        assert ev.event_type == "dispatch.equipment.starved"
        assert ev.source == "dispatch"
        assert ev.payload["equipment_id"] == "eq-1"

    def test_dispatch_evaluated_with_lot_id(self):
        ev = dispatch_evaluated("u-1", "shortest_queue", "eq-1", lot_id="lot-1")
        assert ev.payload["lot_id"] == "lot-1"
        assert ev.payload["unit_id"] == "u-1"

    def test_dispatch_executed_with_lot_id(self):
        ev = dispatch_executed(
            "u-1", "step-1", lot_id="lot-1", destination_equipment_id="eq-1",
        )
        assert ev.payload["lot_id"] == "lot-1"
        assert ev.payload["destination_equipment_id"] == "eq-1"


# ═══════════════════════════════════════════════════════════════════
# Exception Tests — Capacity / Material Capability
# ═══════════════════════════════════════════════════════════════════


class TestCapacityExceptions:
    def test_equipment_at_capacity(self):
        exc = EquipmentAtCapacityException("step-1")
        assert exc.status_code == 422
        assert exc.error_code == "EQUIPMENT_AT_CAPACITY"
        assert exc.details["step_id"] == "step-1"
        assert "capacity" in str(exc).lower()

    def test_equipment_at_capacity_no_step(self):
        exc = EquipmentAtCapacityException()
        assert exc.details["step_id"] is None

    def test_material_capability_exception(self):
        exc = MaterialCapabilityException("mat-1", "step-1")
        assert exc.status_code == 422
        assert exc.error_code == "MATERIAL_CAPABILITY_MISMATCH"
        assert exc.details["material_id"] == "mat-1"
        assert exc.details["step_id"] == "step-1"
        assert "mat-1" in str(exc)

    def test_material_capability_no_step(self):
        exc = MaterialCapabilityException("mat-2")
        assert exc.details["step_id"] is None

    def test_no_eligible_equipment_with_reason(self):
        exc = NoEligibleEquipmentException("step-1", reason="all queues full")
        assert exc.details["reason"] == "all queues full"
        assert "all queues full" in str(exc)


# ═══════════════════════════════════════════════════════════════════
# Handler Registration Tests
# ═══════════════════════════════════════════════════════════════════


class TestHandlerRegistration:
    def test_handlers_module_importable(self):
        import mes.core.dispatch.handlers  # noqa: F401

    def test_event_handlers_registered(self):
        from mes.framework.events.decorators import get_registered_handlers
        handlers = get_registered_handlers()
        event_types = [h[0] for h in handlers]
        assert "wip.lot.completed" in event_types
        assert "wip.unit.completed" in event_types

    def test_handler_functions_exist(self):
        from mes.core.dispatch.handlers import on_lot_completed, on_unit_completed
        import inspect
        assert inspect.iscoroutinefunction(on_lot_completed)
        assert inspect.iscoroutinefunction(on_unit_completed)
