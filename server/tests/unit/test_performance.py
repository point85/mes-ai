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
    production_counter_updated,
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
    CounterIncrementRequest,
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


# ═══════════════════════════════════════════════════════════════════
# CounterIncrementRequest Schema Tests
# ═══════════════════════════════════════════════════════════════════


class TestCounterIncrementRequestSchema:
    def test_minimal_defaults(self):
        schema = CounterIncrementRequest(equipment_id=uuid.uuid4())
        assert schema.good_delta == 0
        assert schema.reject_delta == 0
        assert schema.rework_delta == 0
        assert schema.source == "manual"
        assert schema.order_id is None

    def test_full_fields(self):
        eid = uuid.uuid4()
        oid = uuid.uuid4()
        schema = CounterIncrementRequest(
            equipment_id=eid,
            order_id=oid,
            good_delta=10,
            reject_delta=2,
            rework_delta=1,
            source="packml-opcua",
        )
        assert schema.equipment_id == eid
        assert schema.order_id == oid
        assert schema.good_delta == 10
        assert schema.reject_delta == 2
        assert schema.rework_delta == 1
        assert schema.source == "packml-opcua"

    def test_negative_good_delta_fails(self):
        with pytest.raises(ValidationError):
            CounterIncrementRequest(equipment_id=uuid.uuid4(), good_delta=-1)

    def test_negative_reject_delta_fails(self):
        with pytest.raises(ValidationError):
            CounterIncrementRequest(equipment_id=uuid.uuid4(), reject_delta=-1)

    def test_negative_rework_delta_fails(self):
        with pytest.raises(ValidationError):
            CounterIncrementRequest(equipment_id=uuid.uuid4(), rework_delta=-1)


# ═══════════════════════════════════════════════════════════════════
# production_counter_updated Event Tests
# ═══════════════════════════════════════════════════════════════════


class TestProductionCounterUpdatedEvent:
    def test_basic_event(self):
        ev = production_counter_updated("eq-1", good_delta=5, reject_delta=1)
        assert ev.event_type == "production.counter.updated"
        assert ev.source == "performance"
        assert ev.payload["equipment_id"] == "eq-1"
        assert ev.payload["good_delta"] == 5
        assert ev.payload["reject_delta"] == 1
        assert ev.payload["rework_delta"] == 0
        assert ev.payload["source_plugin"] == "manual"

    def test_custom_source(self):
        ev = production_counter_updated("eq-2", source_plugin="mqtt-counters")
        assert ev.payload["source_plugin"] == "mqtt-counters"

    def test_all_deltas(self):
        ev = production_counter_updated(
            "eq-3", good_delta=10, reject_delta=2, rework_delta=3,
            source_plugin="packml-opcua-counters",
        )
        assert ev.payload["good_delta"] == 10
        assert ev.payload["reject_delta"] == 2
        assert ev.payload["rework_delta"] == 3


# ═══════════════════════════════════════════════════════════════════
# Service increment_counter Method Exists
# ═══════════════════════════════════════════════════════════════════


class TestCounterServiceIncrementMethod:
    def test_increment_counter_exists(self):
        from mes.core.performance.service import ProductionCounterService
        assert hasattr(ProductionCounterService, "increment_counter")

    def test_increment_counter_is_static(self):
        from mes.core.performance.service import ProductionCounterService
        import inspect
        assert isinstance(
            inspect.getattr_static(ProductionCounterService, "increment_counter"),
            staticmethod,
        )


# ═══════════════════════════════════════════════════════════════════
# Route — counters/increment endpoint registered
# ═══════════════════════════════════════════════════════════════════


class TestCounterIncrementRoute:
    def test_increment_route_registered(self):
        from mes.core.performance.routes import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/performance/counters/increment" in paths


# ═══════════════════════════════════════════════════════════════════
# Plugin Tests — PackML OPC-UA Counters
# ═══════════════════════════════════════════════════════════════════


class TestPackMLOpcuaCountersPlugin:
    def test_plugin_class_importable(self):
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin
        assert PackMLOpcuaCountersPlugin is not None

    def test_plugin_inherits_mesplugin(self):
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin
        from mes.framework.plugin.base import MESPlugin
        assert issubclass(PackMLOpcuaCountersPlugin, MESPlugin)

    @pytest.mark.asyncio
    async def test_initialize_stores_config(self):
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin
        plugin = PackMLOpcuaCountersPlugin()
        cfg = {"poll_interval_sec": 10, "subscription_interval_ms": 500}
        await plugin.initialize(cfg)
        assert plugin._config == cfg

    @pytest.mark.asyncio
    async def test_stop_idempotent(self):
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin
        plugin = PackMLOpcuaCountersPlugin()
        await plugin.initialize({})
        await plugin.stop()  # Should not raise even if never started

    def test_equipment_state_tracks_deltas(self):
        from plugins.system.packml_opcua_counters.plugin import _EquipmentState
        eid = uuid.uuid4()
        state = _EquipmentState(eid)
        assert state.last_good is None
        assert state.last_reject is None
        state.last_good = 100
        state.last_reject = 5
        assert state.last_good == 100


class TestPackMLOpcuaDeltaDetection:
    """Test delta detection logic without requiring OPC-UA connection."""

    @pytest.mark.asyncio
    async def test_first_read_sets_baseline_no_increment(self):
        """First value read should set baseline but not trigger increment."""
        from unittest.mock import AsyncMock, patch
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin, _EquipmentState

        plugin = PackMLOpcuaCountersPlugin()
        await plugin.initialize({})
        eid = uuid.uuid4()
        plugin._equipment_states[eid] = _EquipmentState(eid)

        with patch(
            "mes.framework.db.async_session_factory"
        ) as mock_factory:
            await plugin._process_values(eid, 100, 5)
            # First read — no previous baseline → no DB call
            mock_factory.assert_not_called()

        assert plugin._equipment_states[eid].last_good == 100
        assert plugin._equipment_states[eid].last_reject == 5

    @pytest.mark.asyncio
    async def test_second_read_computes_delta(self):
        """Second read should compute and send delta."""
        from unittest.mock import AsyncMock, patch, MagicMock
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin, _EquipmentState

        plugin = PackMLOpcuaCountersPlugin()
        await plugin.initialize({})
        eid = uuid.uuid4()
        state = _EquipmentState(eid)
        state.last_good = 100
        state.last_reject = 5
        plugin._equipment_states[eid] = state

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "mes.framework.db.async_session_factory",
            return_value=mock_ctx,
        ), patch(
            "mes.core.performance.service.ProductionCounterService.increment_counter",
            new_callable=AsyncMock,
        ) as mock_inc:
            await plugin._process_values(eid, 110, 7)
            mock_inc.assert_awaited_once_with(
                mock_session,
                equipment_id=eid,
                good_delta=10,
                reject_delta=2,
                source_plugin="packml-opcua-counters",
            )

    @pytest.mark.asyncio
    async def test_no_change_no_increment(self):
        """If values don't change, no DB call."""
        from unittest.mock import AsyncMock, patch
        from plugins.system.packml_opcua_counters.plugin import PackMLOpcuaCountersPlugin, _EquipmentState

        plugin = PackMLOpcuaCountersPlugin()
        await plugin.initialize({})
        eid = uuid.uuid4()
        state = _EquipmentState(eid)
        state.last_good = 100
        state.last_reject = 5
        plugin._equipment_states[eid] = state

        with patch(
            "mes.framework.db.async_session_factory"
        ) as mock_factory:
            await plugin._process_values(eid, 100, 5)
            mock_factory.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# Plugin Tests — MQTT Counters
# ═══════════════════════════════════════════════════════════════════


class TestMQTTCountersPlugin:
    def test_plugin_class_importable(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        assert MQTTCountersPlugin is not None

    def test_plugin_inherits_mesplugin(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        from mes.framework.plugin.base import MESPlugin
        assert issubclass(MQTTCountersPlugin, MESPlugin)

    @pytest.mark.asyncio
    async def test_initialize_stores_config(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        plugin = MQTTCountersPlugin()
        cfg = {"broker_host": "10.0.0.5", "broker_port": 1883}
        await plugin.initialize(cfg)
        assert plugin._config == cfg

    @pytest.mark.asyncio
    async def test_stop_idempotent(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        plugin = MQTTCountersPlugin()
        await plugin.initialize({})
        await plugin.stop()  # Should not raise even if never started


class TestMQTTCountersTopicParsing:
    """Test equipment_id extraction from MQTT topic paths."""

    def test_valid_topic(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        eid = uuid.uuid4()
        topic = f"mes/equipment/{eid}/counters"
        result = MQTTCountersPlugin._extract_equipment_id(topic)
        assert result == eid

    def test_invalid_uuid(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        result = MQTTCountersPlugin._extract_equipment_id("mes/equipment/not-a-uuid/counters")
        assert result is None

    def test_wrong_suffix(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        eid = uuid.uuid4()
        result = MQTTCountersPlugin._extract_equipment_id(f"mes/equipment/{eid}/status")
        assert result is None

    def test_short_topic(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        result = MQTTCountersPlugin._extract_equipment_id("too/short")
        assert result is None


class TestMQTTCountersPayloadParsing:
    """Test JSON payload parsing for MQTT counter messages."""

    def test_valid_json_bytes(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        raw = b'{"good_delta": 10, "reject_delta": 1}'
        result = MQTTCountersPlugin._parse_payload(raw)
        assert result == {"good_delta": 10, "reject_delta": 1}

    def test_valid_json_string(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        raw = '{"good_delta": 5}'
        result = MQTTCountersPlugin._parse_payload(raw)
        assert result == {"good_delta": 5}

    def test_invalid_json(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        result = MQTTCountersPlugin._parse_payload(b"not json")
        assert result is None

    def test_non_object_json(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        result = MQTTCountersPlugin._parse_payload(b"[1, 2, 3]")
        assert result is None

    def test_empty_bytearray(self):
        from plugins.system.mqtt_counters.plugin import MQTTCountersPlugin
        result = MQTTCountersPlugin._parse_payload(bytearray(b"{}"))
        assert result == {}


# ═══════════════════════════════════════════════════════════════════
# OEE Calculation Tests
# ═══════════════════════════════════════════════════════════════════


def _mock_state_log(oee_bucket: str, duration_sec: float, period_end: datetime):
    """Create a mock state log with a given bucket and duration."""
    ended_at = period_end
    started_at = ended_at - __import__("datetime").timedelta(seconds=duration_sec)
    return types.SimpleNamespace(
        oee_bucket=oee_bucket,
        started_at=started_at,
        ended_at=ended_at,
    )


def _mock_counter_row(
    total_good=0,
    total_reject=0,
    total_rework=0,
    avg_cycle_time=None,
):
    """Create a mock row from the counter aggregate query."""
    return types.SimpleNamespace(
        total_good=total_good,
        total_reject=total_reject,
        total_rework=total_rework,
        avg_cycle_time=avg_cycle_time,
    )


def _mock_equipment_material(design_speed: float, denominator_multiplier: float = 3600.0):
    """Create a mock EquipmentMaterial with a rate UoM."""
    denominator_uom = types.SimpleNamespace(multiplier=denominator_multiplier)
    rate_uom = types.SimpleNamespace(denominator_uom=denominator_uom)
    return types.SimpleNamespace(
        design_speed=design_speed,
        design_speed_unit=rate_uom,
    )


class TestOEECalculation:
    """Test OEEService.calculate_oee with mocked async sessions."""

    @pytest.mark.asyncio
    async def test_standard_oee(self):
        """OEE with realistic Availability/Performance/Quality losses."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        # 6h uptime value-add, 1h uptime non-value, 0.5h planned downtime, 0.5h unplanned
        logs = [
            _mock_state_log("uptime_value_add", 21600, period_end),   # 6h = 21600s
            _mock_state_log("uptime_non_value", 3600, period_end),    # 1h = 3600s
            _mock_state_log("downtime_planned", 1800, period_end),    # 0.5h
            _mock_state_log("downtime_unplanned", 1800, period_end),  # 0.5h
        ]

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = logs

        # 900 good, 50 reject, 20 rework = 970 total
        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row(900, 50, 20)

        # EquipmentMaterial: 120 EA/h → 30 sec/unit
        em = _mock_equipment_material(120.0, 3600.0)
        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = em

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch("mes.core.performance.service.event_bus.publish", new_callable=AsyncMock):
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )

        # Availability = 25200 / (25200 + 3600) = 0.875
        assert result["availability"] == round(25200 / 28800, 4)
        # Performance = (30 * 970) / 25200 = 1.1547... capped to 1.0
        assert result["performance"] == 1.0
        # Quality = 900 / 970
        assert result["quality"] == round(900 / 970, 4)
        # OEE = availability * performance * quality (from exact values, then rounded)
        expected_oee = round((25200 / 28800) * 1.0 * (900 / 970), 4)
        assert result["oee"] == expected_oee
        # Six big losses present
        assert result["six_big_losses"]["planned_downtime_sec"] == 1800.0
        assert result["six_big_losses"]["unplanned_downtime_sec"] == 1800.0
        assert result["six_big_losses"]["quality_loss_count"] == 70

    @pytest.mark.asyncio
    async def test_perfect_oee(self):
        """100% OEE: no downtime, running at exactly design speed, all good."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        # 8h of value-add uptime, no downtime
        logs = [_mock_state_log("uptime_value_add", 28800, period_end)]

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = logs

        # At 120 EA/h for 8h → 960 pieces, all good
        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row(960, 0, 0)

        # 120 EA/h → 30 sec/unit; 30 * 960 = 28800 = run_time exactly
        em = _mock_equipment_material(120.0, 3600.0)
        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = em

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch("mes.core.performance.service.event_bus.publish", new_callable=AsyncMock):
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )

        assert result["availability"] == 1.0
        assert result["performance"] == 1.0
        assert result["quality"] == 1.0
        assert result["oee"] == 1.0
        assert result["six_big_losses"]["speed_loss_sec"] == 0

    @pytest.mark.asyncio
    async def test_zero_data(self):
        """No state logs and no counters → all zeros."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = []

        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row()

        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch("mes.core.performance.service.event_bus.publish", new_callable=AsyncMock):
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )

        assert result["availability"] == 0.0
        assert result["performance"] == 0.0
        assert result["quality"] == 0.0
        assert result["oee"] == 0.0

    @pytest.mark.asyncio
    async def test_performance_from_counter_fallback(self):
        """When no EquipmentMaterial exists, falls back to counter ideal_cycle_time_sec."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        # 8h uptime
        logs = [_mock_state_log("uptime_value_add", 28800, period_end)]

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = logs

        # 800 good, counter has avg ideal_cycle_time_sec = 30
        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row(800, 0, 0, avg_cycle_time=30.0)

        # No EquipmentMaterial
        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch("mes.core.performance.service.event_bus.publish", new_callable=AsyncMock):
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )

        assert result["availability"] == 1.0
        # Performance = (30 * 800) / 28800 = 0.8333
        expected_perf = round((30.0 * 800) / 28800, 4)
        assert result["performance"] == expected_perf
        assert result["quality"] == 1.0
        assert result["details"]["ideal_cycle_time_sec"] == 30.0

    @pytest.mark.asyncio
    async def test_six_big_losses_breakdown(self):
        """Verify six big losses are properly populated."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        # 5h value-add, 1h non-value, 1h planned, 0.5h unplanned, 0.5h excluded
        logs = [
            _mock_state_log("uptime_value_add", 18000, period_end),
            _mock_state_log("uptime_non_value", 3600, period_end),
            _mock_state_log("downtime_planned", 3600, period_end),
            _mock_state_log("downtime_unplanned", 1800, period_end),
            _mock_state_log("excluded", 1800, period_end),
        ]

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = logs

        # 600 good, 30 reject, 10 rework
        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row(600, 30, 10)

        em = _mock_equipment_material(120.0, 3600.0)
        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = em

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch("mes.core.performance.service.event_bus.publish", new_callable=AsyncMock):
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )

        losses = result["six_big_losses"]
        assert losses["planned_downtime_sec"] == 3600.0
        assert losses["unplanned_downtime_sec"] == 1800.0
        assert losses["quality_loss_count"] == 40

        # Speed loss = run_time - (ideal_cycle * total_count) = 21600 - (30 * 640) = 2400
        assert losses["speed_loss_sec"] == 2400.0

        # Excluded time should be in details, not in planned production time
        assert result["details"]["excluded_time_sec"] == 1800.0
        # Planned Production Time = 21600 + 3600 + 1800 = 27000 (excludes "excluded")
        assert result["details"]["planned_production_time_sec"] == 27000.0

    @pytest.mark.asyncio
    async def test_design_speed_minutes_denominator(self):
        """Test design speed with minutes as denominator (e.g. EA/min)."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        # 1h = 3600s uptime
        logs = [_mock_state_log("uptime_value_add", 3600, period_end)]

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = logs

        # 120 good pieces
        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row(120, 0, 0)

        # 2 EA/min → denominator min has multiplier=60 → 60/2 = 30 sec/unit
        # 30 * 120 / 3600 = 1.0
        em = _mock_equipment_material(2.0, 60.0)
        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = em

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch("mes.core.performance.service.event_bus.publish", new_callable=AsyncMock):
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )

        assert result["performance"] == 1.0

    @pytest.mark.asyncio
    async def test_oee_event_emitted(self):
        """Verify the oee_calculated event is published."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from mes.core.performance.service import OEEService

        eid = uuid.uuid4()
        period_end = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

        logs = [_mock_state_log("uptime_value_add", 28800, period_end)]

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = logs

        mock_counter_result = MagicMock()
        mock_counter_result.one.return_value = _mock_counter_row(960, 0, 0)

        em = _mock_equipment_material(120.0, 3600.0)
        mock_em_result = MagicMock()
        mock_em_result.scalar_one_or_none.return_value = em

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[mock_logs_result, mock_counter_result, mock_em_result],
        )

        with patch(
            "mes.core.performance.service.event_bus.publish",
            new_callable=AsyncMock,
        ) as mock_publish:
            result = await OEEService.calculate_oee(
                mock_session, eid, period_start, period_end,
            )
            mock_publish.assert_awaited_once()
            event = mock_publish.call_args[0][0]
            assert event.event_type == "performance.oee.calculated"
            assert event.payload["oee"] == result["oee"]


class TestOEEResultSchemaWithSixBigLosses:
    """Validate the updated OEEResult schema includes six_big_losses."""

    def test_oee_result_with_losses(self):
        result = OEEResult(
            equipment_id=uuid.uuid4(),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            availability=0.875,
            performance=0.95,
            quality=0.93,
            oee=0.773,
            details={"run_time_sec": 25200},
            six_big_losses={
                "planned_downtime_sec": 1800,
                "unplanned_downtime_sec": 1800,
                "speed_loss_sec": 1200,
                "quality_loss_count": 70,
            },
        )
        assert result.six_big_losses["planned_downtime_sec"] == 1800
        assert result.six_big_losses["quality_loss_count"] == 70

    def test_oee_result_without_losses(self):
        result = OEEResult(
            equipment_id=uuid.uuid4(),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            availability=1.0,
            performance=1.0,
            quality=1.0,
            oee=1.0,
        )
        assert result.six_big_losses is None
