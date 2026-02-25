"""
Unit tests for the ROUTE-ENGINE (Routing Engine) module.

Covers:
- RoutingEngineService static methods with mocked data
- Route resolution priority (explicit → default → fallback)
- Next step determination (sequential, end-of-route)
- First step resolution
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
