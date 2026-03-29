"""
Unit tests for equipment state machine engine, models, schemas and plugins.

Covers:
- EquipmentStateModel DB model
- StateDefinitionSchema, TransitionDefinitionSchema validation
- EquipmentStateModelRead schema
- EquipmentTransitionRequest schema
- EquipmentCurrentStateRead schema
- EquipmentStateEngine helpers (_find_state_def, _is_transition_valid, get_valid_next_states)
- InvalidStateTransitionException
- PackML plugin state definitions
- SEMI E10 plugin state definitions
- New router path registration
- Physical model Equipment.state_model_id column
"""

from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

# Ensure the plugins directory is importable
_server_root = Path(__file__).resolve().parents[2]
_plugins_path = str(_server_root / "plugins")
if _plugins_path not in sys.path:
    sys.path.insert(0, _plugins_path)

from mes.core.performance.engine import (
    DEFAULT_DISPATCH_CATEGORY,
    DEFAULT_OEE_BUCKET,
    DEFAULT_STATE,
    EquipmentStateEngine,
)
from mes.core.performance.exceptions import InvalidStateTransitionException
from mes.core.performance.models import EquipmentStateModel
from mes.core.performance.schemas import (
    DISPATCH_CATEGORIES,
    OEE_BUCKETS,
    EquipmentCurrentStateRead,
    EquipmentStateModelRead,
    EquipmentTransitionRequest,
    StateDefinitionSchema,
    TransitionDefinitionSchema,
)


# ─── Helpers ──────────────────────────────────────────────────────────

SAMPLE_STATES = [
    {"name": "Idle",    "dispatch_category": "available", "oee_bucket": "uptime_non_value"},
    {"name": "Running", "dispatch_category": "busy",      "oee_bucket": "uptime_value_add"},
    {"name": "Down",    "dispatch_category": "unavailable_unplanned", "oee_bucket": "downtime_unplanned"},
]

SAMPLE_TRANSITIONS = [
    {"from_state": "Idle",    "to_state": "Running"},
    {"from_state": "Running", "to_state": "Idle"},
    {"from_state": "Running", "to_state": "Down"},
    {"from_state": "Down",    "to_state": "Idle"},
]


def _make_state_model_obj(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "model_id": "test-model",
        "name": "Test Model",
        "description": "A test model",
        "initial_state": "Idle",
        "states": SAMPLE_STATES,
        "transitions": SAMPLE_TRANSITIONS,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═══════════════════════════════════════════════════════════════════
# EquipmentStateModel — DB model
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentStateModelTable:
    def test_tablename(self):
        assert EquipmentStateModel.__tablename__ == "equipment_state_models"

    def test_mapper_columns(self):
        cols = {c.key for c in EquipmentStateModel.__table__.columns}
        assert "model_id" in cols
        assert "name" in cols
        assert "description" in cols
        assert "initial_state" in cols
        assert "states" in cols
        assert "transitions" in cols

    def test_repr(self):
        m = EquipmentStateModel()
        m.id = uuid.uuid4()
        m.model_id = "packml"
        m.name = "PackML"
        r = repr(m)
        assert "packml" in r or "PackML" in r


# ═══════════════════════════════════════════════════════════════════
# StateDefinitionSchema
# ═══════════════════════════════════════════════════════════════════


class TestStateDefinitionSchema:
    def test_valid_state(self):
        s = StateDefinitionSchema(
            name="Idle",
            dispatch_category="available",
            oee_bucket="uptime_non_value",
        )
        assert s.name == "Idle"
        assert s.display_name is None

    def test_with_display_name(self):
        s = StateDefinitionSchema(
            name="Execute",
            display_name="Executing",
            dispatch_category="busy",
            oee_bucket="uptime_value_add",
        )
        assert s.display_name == "Executing"

    def test_invalid_dispatch_category(self):
        with pytest.raises(ValidationError, match="dispatch_category"):
            StateDefinitionSchema(
                name="X",
                dispatch_category="bogus",
                oee_bucket="uptime_value_add",
            )

    def test_invalid_oee_bucket(self):
        with pytest.raises(ValidationError, match="oee_bucket"):
            StateDefinitionSchema(
                name="X",
                dispatch_category="available",
                oee_bucket="bogus",
            )

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            StateDefinitionSchema(
                name="",
                dispatch_category="available",
                oee_bucket="uptime_non_value",
            )


# ═══════════════════════════════════════════════════════════════════
# TransitionDefinitionSchema
# ═══════════════════════════════════════════════════════════════════


class TestTransitionDefinitionSchema:
    def test_valid_transition(self):
        t = TransitionDefinitionSchema(from_state="Idle", to_state="Running")
        assert t.from_state == "Idle"
        assert t.trigger is None

    def test_with_trigger(self):
        t = TransitionDefinitionSchema(
            from_state="Idle", to_state="Running", trigger="Start command",
        )
        assert t.trigger == "Start command"

    def test_empty_from_rejected(self):
        with pytest.raises(ValidationError):
            TransitionDefinitionSchema(from_state="", to_state="Running")


# ═══════════════════════════════════════════════════════════════════
# EquipmentStateModelRead
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentStateModelReadSchema:
    def test_from_attributes(self):
        obj = _make_state_model_obj()
        schema = EquipmentStateModelRead.model_validate(obj, from_attributes=True)
        assert schema.model_id == "test-model"
        assert schema.initial_state == "Idle"
        assert len(schema.states) == 3
        assert len(schema.transitions) == 4


# ═══════════════════════════════════════════════════════════════════
# EquipmentTransitionRequest
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentTransitionRequestSchema:
    def test_minimal(self):
        r = EquipmentTransitionRequest(new_state="Execute")
        assert r.new_state == "Execute"
        assert r.reason_code is None
        assert r.notes is None

    def test_full(self):
        r = EquipmentTransitionRequest(
            new_state="Execute", reason_code="OP_START", notes="Operator started",
        )
        assert r.reason_code == "OP_START"

    def test_empty_state_rejected(self):
        with pytest.raises(ValidationError):
            EquipmentTransitionRequest(new_state="")


# ═══════════════════════════════════════════════════════════════════
# EquipmentCurrentStateRead
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentCurrentStateReadSchema:
    def test_default_state(self):
        s = EquipmentCurrentStateRead(
            equipment_id=uuid.uuid4(),
            state_model="default",
            state="running",
            dispatch_category="available",
            oee_bucket="uptime_value_add",
        )
        assert s.valid_transitions == []
        assert s.started_at is None

    def test_with_transitions(self):
        s = EquipmentCurrentStateRead(
            equipment_id=uuid.uuid4(),
            state_model="packml",
            state="Idle",
            dispatch_category="available",
            oee_bucket="uptime_non_value",
            started_at=datetime.now(timezone.utc),
            valid_transitions=[{"from_state": "Idle", "to_state": "Starting"}],
        )
        assert len(s.valid_transitions) == 1


# ═══════════════════════════════════════════════════════════════════
# Engine — Pure helper methods (no DB required)
# ═══════════════════════════════════════════════════════════════════


class TestEngineHelpers:
    def test_find_state_def_found(self):
        result = EquipmentStateEngine._find_state_def(SAMPLE_STATES, "Running")
        assert result is not None
        assert result["dispatch_category"] == "busy"

    def test_find_state_def_not_found(self):
        result = EquipmentStateEngine._find_state_def(SAMPLE_STATES, "NoSuch")
        assert result is None

    def test_is_transition_valid_yes(self):
        assert EquipmentStateEngine._is_transition_valid(
            SAMPLE_TRANSITIONS, "Idle", "Running",
        ) is True

    def test_is_transition_valid_no(self):
        assert EquipmentStateEngine._is_transition_valid(
            SAMPLE_TRANSITIONS, "Idle", "Down",
        ) is False

    def test_get_valid_next_states(self):
        result = EquipmentStateEngine.get_valid_next_states(
            SAMPLE_TRANSITIONS, "Running",
        )
        assert len(result) == 2
        targets = {t["to_state"] for t in result}
        assert targets == {"Idle", "Down"}

    def test_get_valid_next_states_from_terminal(self):
        result = EquipmentStateEngine.get_valid_next_states(
            SAMPLE_TRANSITIONS, "NoSuch",
        )
        assert result == []


# ═══════════════════════════════════════════════════════════════════
# Engine — Default constants
# ═══════════════════════════════════════════════════════════════════


class TestEngineDefaults:
    def test_default_state(self):
        assert DEFAULT_STATE == "running"

    def test_default_dispatch_category(self):
        assert DEFAULT_DISPATCH_CATEGORY in DISPATCH_CATEGORIES

    def test_default_oee_bucket(self):
        assert DEFAULT_OEE_BUCKET in OEE_BUCKETS


# ═══════════════════════════════════════════════════════════════════
# InvalidStateTransitionException
# ═══════════════════════════════════════════════════════════════════


class TestInvalidStateTransitionException:
    def test_construction(self):
        exc = InvalidStateTransitionException("Idle → Down not allowed")
        assert exc.status_code == 409
        assert exc.error_code == "INVALID_STATE_TRANSITION"
        assert "Idle → Down" in str(exc) or "Idle" in str(exc)


# ═══════════════════════════════════════════════════════════════════
# PackML Plugin — State definitions
# ═══════════════════════════════════════════════════════════════════


class TestPackMLPlugin:
    def test_model_constants(self):
        from system.packml_availability.plugin import (
            INITIAL_STATE,
            MODEL_ID,
            MODEL_NAME,
            STATES,
            TRANSITIONS,
        )
        assert MODEL_ID == "packml"
        assert "PackML" in MODEL_NAME
        assert INITIAL_STATE == "Stopped"

    def test_17_states_defined(self):
        from system.packml_availability.plugin import STATES
        assert len(STATES) == 17

    def test_state_names(self):
        from system.packml_availability.plugin import STATES
        names = {s["name"] for s in STATES}
        expected = {
            "Stopped", "Idle", "Starting", "Execute", "Completing", "Complete",
            "Resetting", "Holding", "Held", "Unholding", "Suspending",
            "Suspended", "Unsuspending", "Stopping", "Aborting", "Aborted",
            "Clearing",
        }
        assert names == expected

    def test_all_states_have_canonical_fields(self):
        from system.packml_availability.plugin import STATES
        for s in STATES:
            assert s["dispatch_category"] in DISPATCH_CATEGORIES, f"{s['name']} bad dispatch"
            assert s["oee_bucket"] in OEE_BUCKETS, f"{s['name']} bad oee_bucket"

    def test_execute_is_value_add(self):
        from system.packml_availability.plugin import STATES
        execute = next(s for s in STATES if s["name"] == "Execute")
        assert execute["dispatch_category"] == "busy"
        assert execute["oee_bucket"] == "uptime_value_add"

    def test_idle_is_available(self):
        from system.packml_availability.plugin import STATES
        idle = next(s for s in STATES if s["name"] == "Idle")
        assert idle["dispatch_category"] == "available"

    def test_held_is_unplanned(self):
        from system.packml_availability.plugin import STATES
        held = next(s for s in STATES if s["name"] == "Held")
        assert held["dispatch_category"] == "unavailable_unplanned"
        assert held["oee_bucket"] == "downtime_unplanned"

    def test_production_cycle_transitions(self):
        """Stopped→Resetting→Idle→Starting→Execute→Completing→Complete→Resetting."""
        from system.packml_availability.plugin import TRANSITIONS
        cycle = [
            ("Stopped", "Resetting"),
            ("Resetting", "Idle"),
            ("Idle", "Starting"),
            ("Starting", "Execute"),
            ("Execute", "Completing"),
            ("Completing", "Complete"),
            ("Complete", "Resetting"),
        ]
        for src, dst in cycle:
            assert EquipmentStateEngine._is_transition_valid(TRANSITIONS, src, dst), (
                f"Missing transition {src}→{dst}"
            )

    def test_hold_branch(self):
        from system.packml_availability.plugin import TRANSITIONS
        hold = [
            ("Execute", "Holding"),
            ("Holding", "Held"),
            ("Held", "Unholding"),
            ("Unholding", "Execute"),
        ]
        for src, dst in hold:
            assert EquipmentStateEngine._is_transition_valid(TRANSITIONS, src, dst)

    def test_suspend_branch(self):
        from system.packml_availability.plugin import TRANSITIONS
        suspend = [
            ("Execute", "Suspending"),
            ("Suspending", "Suspended"),
            ("Suspended", "Unsuspending"),
            ("Unsuspending", "Execute"),
        ]
        for src, dst in suspend:
            assert EquipmentStateEngine._is_transition_valid(TRANSITIONS, src, dst)

    def test_abort_from_any_normal_state(self):
        from system.packml_availability.plugin import TRANSITIONS
        abortable = [
            "Stopped", "Idle", "Starting", "Execute", "Completing",
            "Complete", "Resetting", "Holding", "Held", "Unholding",
            "Suspending", "Suspended", "Unsuspending", "Stopping",
        ]
        for s in abortable:
            assert EquipmentStateEngine._is_transition_valid(TRANSITIONS, s, "Aborting"), (
                f"Should be able to abort from {s}"
            )

    def test_abort_cannot_from_aborting_aborted_clearing(self):
        from system.packml_availability.plugin import TRANSITIONS
        for s in ["Aborting", "Aborted", "Clearing"]:
            assert not EquipmentStateEngine._is_transition_valid(TRANSITIONS, s, "Aborting"), (
                f"Should NOT be able to abort from {s}"
            )

    def test_clearing_leads_to_stopped(self):
        from system.packml_availability.plugin import TRANSITIONS
        assert EquipmentStateEngine._is_transition_valid(TRANSITIONS, "Clearing", "Stopped")

    def test_plugin_class_exists(self):
        from system.packml_availability.plugin import PackMLAvailabilityPlugin
        p = PackMLAvailabilityPlugin()
        assert hasattr(p, "initialize")
        assert hasattr(p, "start")
        assert hasattr(p, "stop")


# ═══════════════════════════════════════════════════════════════════
# SEMI E10 Plugin — State definitions
# ═══════════════════════════════════════════════════════════════════


class TestSEMIE10Plugin:
    def test_model_constants(self):
        from system.semi_e10_availability.plugin import (
            INITIAL_STATE,
            MODEL_ID,
            MODEL_NAME,
            STATES,
            TRANSITIONS,
        )
        assert MODEL_ID == "semi_e10"
        assert "SEMI" in MODEL_NAME or "E10" in MODEL_NAME
        assert INITIAL_STATE == "Standby"

    def test_6_states_defined(self):
        from system.semi_e10_availability.plugin import STATES
        assert len(STATES) == 6

    def test_state_names(self):
        from system.semi_e10_availability.plugin import STATES
        names = {s["name"] for s in STATES}
        expected = {
            "Productive", "Standby", "Engineering",
            "Scheduled Downtime", "Unscheduled Downtime", "Non-Scheduled",
        }
        assert names == expected

    def test_all_states_have_canonical_fields(self):
        from system.semi_e10_availability.plugin import STATES
        for s in STATES:
            assert s["dispatch_category"] in DISPATCH_CATEGORIES, f"{s['name']} bad dispatch"
            assert s["oee_bucket"] in OEE_BUCKETS, f"{s['name']} bad oee_bucket"

    def test_productive_is_value_add(self):
        from system.semi_e10_availability.plugin import STATES
        prod = next(s for s in STATES if s["name"] == "Productive")
        assert prod["dispatch_category"] == "busy"
        assert prod["oee_bucket"] == "uptime_value_add"

    def test_non_scheduled_is_excluded(self):
        from system.semi_e10_availability.plugin import STATES
        ns = next(s for s in STATES if s["name"] == "Non-Scheduled")
        assert ns["oee_bucket"] == "excluded"

    def test_all_to_all_transitions(self):
        """SEMI E10 allows free transitions between all states."""
        from system.semi_e10_availability.plugin import STATES, TRANSITIONS
        names = [s["name"] for s in STATES]
        for src in names:
            for dst in names:
                if src != dst:
                    assert EquipmentStateEngine._is_transition_valid(
                        TRANSITIONS, src, dst,
                    ), f"Missing transition {src}→{dst}"

    def test_no_self_transitions(self):
        from system.semi_e10_availability.plugin import STATES, TRANSITIONS
        names = [s["name"] for s in STATES]
        for name in names:
            assert not EquipmentStateEngine._is_transition_valid(
                TRANSITIONS, name, name,
            ), f"Self-transition not expected for {name}"

    def test_transition_count(self):
        """6 states × 5 destinations = 30 transitions."""
        from system.semi_e10_availability.plugin import TRANSITIONS
        assert len(TRANSITIONS) == 30

    def test_plugin_class_exists(self):
        from system.semi_e10_availability.plugin import SEMIE10AvailabilityPlugin
        p = SEMIE10AvailabilityPlugin()
        assert hasattr(p, "initialize")
        assert hasattr(p, "start")
        assert hasattr(p, "stop")


# ═══════════════════════════════════════════════════════════════════
# Router — New paths registered
# ═══════════════════════════════════════════════════════════════════


class TestStateRouterPaths:
    def test_state_model_routes_registered(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]  # type: ignore[attr-defined]
        assert "/api/v1/performance/state-models" in paths
        assert "/api/v1/performance/state-models/{model_id}" in paths

    def test_equipment_transition_route(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]  # type: ignore[attr-defined]
        assert "/api/v1/performance/equipment/{equip_id}/transition" in paths

    def test_current_state_route(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]  # type: ignore[attr-defined]
        assert "/api/v1/performance/equipment/{equip_id}/current-state" in paths


# ═══════════════════════════════════════════════════════════════════
# Equipment.state_model_id column
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentStateModelColumn:
    def test_column_exists(self):
        from mes.core.physical_model.models import Equipment
        cols = {c.key for c in Equipment.__table__.columns}
        assert "state_model_id" in cols

    def test_column_nullable(self):
        from mes.core.physical_model.models import Equipment
        col = Equipment.__table__.columns["state_model_id"]
        assert col.nullable is True
