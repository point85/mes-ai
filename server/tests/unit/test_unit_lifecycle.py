"""
Unit tests for the complete production unit lifecycle — service-layer execution.

Covers every stage from unit creation through order closing:
  1. Unit creation         — UnitService.create_unit
  2. Unit start            — UnitService.start_unit (queued → in_process)
  3. Unit step completion  — UnitService.complete_unit_step (history close, result)
  4. Unit move             — UnitService.move_unit (next step / final-step completion)
  5. Unit hold / release   — UnitService.hold_unit, release_hold_unit
  6. Unit scrap            — UnitService.scrap_unit (status + order increment)
  7. Data collection       — DataPointService.collect with unit_id
  8. Quality test result   — TestResultService.record_result with unit_id
  9. ERP outbound handler  — on_unit_completed_erp_report (enqueue, qty=1 logic)
 10. Full lifecycle seq    — create → start → complete → move (final) event sequence
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Register all SQLAlchemy models so mapper relationships resolve correctly.
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
import mes.adapters.erp.queue  # noqa: F401
import mes.adapters.erp.inbound_queue  # noqa: F401

from mes.core.wip.service import UnitService
from mes.core.wip.exceptions import (
    DuplicateSerialNumberException,
    InvalidWIPTransitionException,
)
from mes.core.operations.service import OperationsRequestService


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_unit(**overrides) -> MagicMock:
    """Create a MagicMock behaving like a Unit ORM instance."""
    defaults = dict(
        id=_uuid(), serial_number="SN-001", order_id=_uuid(), product_id=_uuid(),
        material_id=None, current_step_id=_uuid(), current_equipment_id=None,
        status="queued", is_active=True,
        created_at=_now(), updated_at=_now(),
    )
    defaults.update(overrides)
    unit = MagicMock()
    unit.configure_mock(**defaults)
    return unit


def _make_order(**overrides) -> MagicMock:
    defaults = dict(
        id=_uuid(), order_number="ORD-001", status="in_progress",
        quantity_ordered=100, quantity_completed=0, quantity_scrapped=0,
        actual_end=None, erp_reference="ERP-12345",
    )
    defaults.update(overrides)
    order = MagicMock()
    order.configure_mock(**defaults)
    return order


def _make_history(**overrides) -> MagicMock:
    defaults = dict(
        id=_uuid(), unit_id=_uuid(), step_id=_uuid(), equipment_id=None,
        entered_at=_now(), exited_at=None,
        result=None, data_snapshot=None, operator_id=None,
    )
    defaults.update(overrides)
    hist = MagicMock()
    hist.configure_mock(**defaults)
    return hist


def _make_step(**overrides) -> MagicMock:
    defaults = dict(
        id=_uuid(), route_id=_uuid(), name="Assembly",
        sequence=10, step_type="production",
        erp_operation_number="0010",
    )
    defaults.update(overrides)
    step = MagicMock()
    step.configure_mock(**defaults)
    return step


def _session_returning(value):
    """Mock AsyncSession where execute → scalar_one_or_none → value."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _session_returning_sequence(*values):
    """Mock AsyncSession that returns different values on successive execute calls."""
    session = AsyncMock()
    results = []
    for v in values:
        r = MagicMock()
        r.scalar_one_or_none.return_value = v
        r.scalars.return_value.all.return_value = v if isinstance(v, list) else [v]
        results.append(r)
    session.execute = AsyncMock(side_effect=results)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ═══════════════════════════════════════════════════════════════════
# 1. UNIT CREATION
# ═══════════════════════════════════════════════════════════════════

class TestUnitCreation:
    """UnitService.create_unit — persist, auto-start order, publish event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.start_order", new_callable=AsyncMock)
    async def test_creates_unit_and_fires_event(self, mock_start_order, mock_publish):
        session = _session_returning(None)  # no duplicate
        unit_data = dict(
            serial_number="SN-NEW", order_id=_uuid(), product_id=_uuid(),
        )
        unit = await UnitService.create_unit(session, **unit_data)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        mock_start_order.assert_awaited_once()
        mock_publish.assert_awaited_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.created"
        assert event.payload["serial_number"] == "SN-NEW"

    @pytest.mark.asyncio
    async def test_rejects_duplicate_serial_number(self):
        existing = _make_unit(serial_number="SN-DUP")
        session = _session_returning(existing)

        with pytest.raises(DuplicateSerialNumberException):
            await UnitService.create_unit(
                session, serial_number="SN-DUP", order_id=_uuid(), product_id=_uuid(),
            )


# ═══════════════════════════════════════════════════════════════════
# 2. UNIT START
# ═══════════════════════════════════════════════════════════════════

class TestUnitStart:
    """UnitService.start_unit — status transition, history creation, event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_start_transitions_to_in_process(self, mock_get, mock_publish):
        unit = _make_unit(status="queued", current_step_id=_uuid())
        mock_get.return_value = unit
        session = AsyncMock()
        session.flush = AsyncMock()

        result = await UnitService.start_unit(session, unit.id)

        assert result.status == "in_process"
        session.add.assert_called_once()        # history record
        session.flush.assert_awaited()
        mock_publish.assert_awaited_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.started"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_start_rejects_completed_unit(self, mock_get):
        unit = _make_unit(status="completed")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.start_unit(session, unit.id)

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_start_rejects_scrapped_unit(self, mock_get):
        unit = _make_unit(status="scrapped")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.start_unit(session, unit.id)

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_start_resolves_first_step_if_none(self, mock_get, mock_publish):
        unit = _make_unit(status="queued", current_step_id=None)
        mock_get.return_value = unit
        first_step = _make_step(sequence=10)
        session = AsyncMock()
        session.flush = AsyncMock()

        with patch(
            "mes.core.routing.service.RoutingEngineService.get_first_step",
            new_callable=AsyncMock, return_value=first_step,
        ) as mock_first:
            await UnitService.start_unit(session, unit.id)
            mock_first.assert_awaited_once()
            assert unit.current_step_id == first_step.id

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_start_assigns_equipment(self, mock_get, mock_publish):
        equip_id = _uuid()
        unit = _make_unit(status="queued", current_step_id=_uuid(), current_equipment_id=None)
        mock_get.return_value = unit
        session = AsyncMock()
        session.flush = AsyncMock()

        await UnitService.start_unit(session, unit.id, equipment_id=equip_id)

        assert unit.current_equipment_id == equip_id
        event = mock_publish.call_args[0][0]
        assert event.payload["equipment_id"] == str(equip_id)


# ═══════════════════════════════════════════════════════════════════
# 3. UNIT STEP COMPLETION
# ═══════════════════════════════════════════════════════════════════

class TestUnitStepCompletion:
    """UnitService.complete_unit_step — history close, result, event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_complete_step_pass_result(self, mock_get, mock_publish):
        step_id = _uuid()
        unit = _make_unit(status="in_process", current_step_id=step_id)
        mock_get.return_value = unit
        history = _make_history(unit_id=unit.id, step_id=step_id)
        session = _session_returning(history)

        result = await UnitService.complete_unit_step(session, unit.id, result="pass")

        assert history.exited_at is not None
        assert history.result == "pass"
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.completed"
        assert event.payload["result"] == "pass"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_complete_step_fail_result(self, mock_get, mock_publish):
        step_id = _uuid()
        unit = _make_unit(status="in_process", current_step_id=step_id)
        mock_get.return_value = unit
        history = _make_history(unit_id=unit.id, step_id=step_id)
        session = _session_returning(history)

        await UnitService.complete_unit_step(session, unit.id, result="fail")

        assert history.result == "fail"
        event = mock_publish.call_args[0][0]
        assert event.payload["result"] == "fail"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_complete_step_with_data_snapshot(self, mock_get, mock_publish):
        step_id = _uuid()
        unit = _make_unit(status="in_process", current_step_id=step_id)
        mock_get.return_value = unit
        history = _make_history(unit_id=unit.id, step_id=step_id)
        session = _session_returning(history)
        snapshot = {"temperature": 72.5, "pressure": 14.7}

        await UnitService.complete_unit_step(
            session, unit.id, result="pass", data_snapshot=snapshot,
        )

        assert history.data_snapshot == snapshot

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_complete_step_defaults_to_pass(self, mock_get, mock_publish):
        step_id = _uuid()
        unit = _make_unit(status="in_process", current_step_id=step_id)
        mock_get.return_value = unit
        history = _make_history(unit_id=unit.id, step_id=step_id)
        session = _session_returning(history)

        await UnitService.complete_unit_step(session, unit.id)

        assert history.result == "pass"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_complete_step_no_history_record(self, mock_get, mock_publish):
        """If no open history exists, step still completes and event fires."""
        unit = _make_unit(status="in_process", current_step_id=_uuid())
        mock_get.return_value = unit
        session = _session_returning(None)  # no history found

        await UnitService.complete_unit_step(session, unit.id)

        mock_publish.assert_awaited_once()
        assert mock_publish.call_args[0][0].event_type == "wip.unit.completed"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_complete_step_rejects_queued_unit(self, mock_get):
        unit = _make_unit(status="queued")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.complete_unit_step(session, unit.id)


# ═══════════════════════════════════════════════════════════════════
# 4. UNIT MOVE
# ═══════════════════════════════════════════════════════════════════

class TestUnitMove:
    """UnitService.move_unit — next-step routing, final-step completion."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_move_to_explicit_target_step(self, mock_get, mock_publish):
        from_step = _uuid()
        to_step = _uuid()
        unit = _make_unit(status="in_process", current_step_id=from_step)
        mock_get.return_value = unit
        session = AsyncMock()
        session.flush = AsyncMock()

        await UnitService.move_unit(session, unit.id, target_step_id=to_step)

        assert unit.current_step_id == to_step
        assert unit.status == "queued"
        assert unit.current_equipment_id is None
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.moved"
        assert event.payload["to_step_id"] == str(to_step)

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_completed", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_move_completes_unit_when_no_next_step(
        self, mock_get, mock_incr_complete, mock_publish,
    ):
        """When routing engine returns None → unit completes, order qty incremented by 1."""
        from_step = _uuid()
        unit = _make_unit(status="in_process", current_step_id=from_step)
        mock_get.return_value = unit
        session = _session_returning(None)  # no history for result inference

        with patch(
            "mes.core.routing.service.RoutingEngineService.get_next_step",
            new_callable=AsyncMock, return_value=None,
        ):
            await UnitService.move_unit(session, unit.id)

        assert unit.status == "completed"
        assert unit.current_step_id is None
        assert unit.current_equipment_id is None
        # Units increment by 1 (default qty)
        mock_incr_complete.assert_awaited_once_with(session, unit.order_id)
        event = mock_publish.call_args[0][0]
        assert event.payload["to_step_id"] is None

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_move_advances_to_routing_engine_next_step(self, mock_get, mock_publish):
        from_step = _uuid()
        next_step = _make_step(id=_uuid(), sequence=20, name="Testing")
        unit = _make_unit(status="in_process", current_step_id=from_step)
        mock_get.return_value = unit
        session = _session_returning(None)  # no history

        with patch(
            "mes.core.routing.service.RoutingEngineService.get_next_step",
            new_callable=AsyncMock, return_value=next_step,
        ):
            await UnitService.move_unit(session, unit.id)

        assert unit.current_step_id == next_step.id
        assert unit.status == "queued"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_move_rejects_completed_unit(self, mock_get):
        unit = _make_unit(status="completed")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.move_unit(session, unit.id)

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_move_rejects_scrapped_unit(self, mock_get):
        unit = _make_unit(status="scrapped")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.move_unit(session, unit.id)


# ═══════════════════════════════════════════════════════════════════
# 5. HOLD / RELEASE
# ═══════════════════════════════════════════════════════════════════

class TestUnitHoldRelease:
    """UnitService.hold_unit, release_hold_unit — status transitions & events."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_hold_sets_on_hold_and_fires_event(self, mock_get, mock_publish):
        unit = _make_unit(status="in_process")
        mock_get.return_value = unit
        session = AsyncMock()
        session.flush = AsyncMock()

        await UnitService.hold_unit(session, unit.id, "Dimensional check")

        assert unit.status == "on_hold"
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.held"
        assert event.payload["reason"] == "Dimensional check"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_hold_rejects_completed_unit(self, mock_get):
        unit = _make_unit(status="completed")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.hold_unit(session, unit.id, "reason")

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_hold_rejects_scrapped_unit(self, mock_get):
        unit = _make_unit(status="scrapped")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.hold_unit(session, unit.id, "reason")

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_release_returns_to_queued(self, mock_get, mock_publish):
        unit = _make_unit(status="on_hold")
        mock_get.return_value = unit
        session = AsyncMock()
        session.flush = AsyncMock()

        await UnitService.release_hold_unit(session, unit.id)

        assert unit.status == "queued"
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.released"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_release_rejects_non_held_unit(self, mock_get):
        unit = _make_unit(status="in_process")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.release_hold_unit(session, unit.id)


# ═══════════════════════════════════════════════════════════════════
# 6. UNIT SCRAP
# ═══════════════════════════════════════════════════════════════════

class TestUnitScrap:
    """UnitService.scrap_unit — status change, order qty update (+1), event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_scrapped", new_callable=AsyncMock)
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_scrap_sets_status_and_increments_order(
        self, mock_get, mock_incr_scrap, mock_publish,
    ):
        step_id = _uuid()
        unit = _make_unit(status="in_process", current_step_id=step_id)
        mock_get.return_value = unit
        session = AsyncMock()
        session.flush = AsyncMock()

        await UnitService.scrap_unit(session, unit.id, "Defective component")

        assert unit.status == "scrapped"
        assert unit.current_equipment_id is None
        # Units increment by 1 (default qty)
        mock_incr_scrap.assert_awaited_once_with(session, unit.order_id)
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.unit.scrapped"
        assert event.payload["reason"] == "Defective component"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_scrap_rejects_already_scrapped(self, mock_get):
        unit = _make_unit(status="scrapped")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.scrap_unit(session, unit.id, "reason")

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock)
    async def test_scrap_rejects_completed(self, mock_get):
        unit = _make_unit(status="completed")
        mock_get.return_value = unit
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await UnitService.scrap_unit(session, unit.id, "reason")


# ═══════════════════════════════════════════════════════════════════
# 7. DATA COLLECTION — with unit_id
# ═══════════════════════════════════════════════════════════════════

class TestDataCollectionForUnit:
    """DataPointService.collect with unit_id — persist, validate, publish event."""

    @pytest.mark.asyncio
    async def test_collect_numeric_for_unit(self):
        from mes.core.data_collection.service import DataPointService

        defn = MagicMock()
        defn.id = _uuid()
        defn.code = "torque"
        defn.data_type = "numeric"
        defn.is_required = False
        defn.lower_limit = 0.0
        defn.upper_limit = 50.0
        defn.enum_values = None

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        unit_id = _uuid()

        with patch("mes.core.data_collection.service.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            result = await DataPointService.collect(
                session, defn, unit_id=unit_id, value_numeric=25.3,
            )

        session.add.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "data.collected"

    @pytest.mark.asyncio
    async def test_collect_rejects_out_of_range_for_unit(self):
        from mes.core.data_collection.service import DataPointService
        from mes.core.data_collection.exceptions import ValueOutOfLimitsException

        defn = MagicMock()
        defn.id = _uuid()
        defn.code = "torque"
        defn.data_type = "numeric"
        defn.is_required = False
        defn.lower_limit = 0.0
        defn.upper_limit = 50.0
        defn.enum_values = None

        session = AsyncMock()

        with pytest.raises(ValueOutOfLimitsException):
            await DataPointService.collect(
                session, defn, unit_id=_uuid(), value_numeric=999.0,
            )


# ═══════════════════════════════════════════════════════════════════
# 8. QUALITY TEST RESULT — with unit_id
# ═══════════════════════════════════════════════════════════════════

class TestQualityResultForUnit:
    """TestResultService.record_result with unit_id — persist, pass/fail event."""

    @pytest.mark.asyncio
    async def test_record_pass_result_for_unit(self):
        from mes.core.quality.service import TestResultService

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("mes.core.quality.service.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            result = await TestResultService.record_result(
                session,
                test_id=_uuid(), unit_id=_uuid(),
                result="pass", tested_at=_now(),
            )

        session.add.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "quality.test.passed"

    @pytest.mark.asyncio
    async def test_record_fail_result_for_unit(self):
        from mes.core.quality.service import TestResultService

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("mes.core.quality.service.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            await TestResultService.record_result(
                session,
                test_id=_uuid(), unit_id=_uuid(),
                result="fail", tested_at=_now(),
            )

        event = mock_publish.call_args[0][0]
        assert event.event_type == "quality.test.failed"


# ═══════════════════════════════════════════════════════════════════
# 9. ERP OUTBOUND — handler enqueue on unit completion
# ═══════════════════════════════════════════════════════════════════

class TestERPOutboundHandlerUnit:
    """on_unit_completed_erp_report — enqueues outbound report with qty=1 logic."""

    @pytest.mark.asyncio
    async def test_handler_enqueues_pass_report(self):
        from mes.adapters.erp.handlers import on_unit_completed_erp_report
        from mes.framework.events.schema import MESEvent

        unit_id = _uuid()
        step_id = _uuid()

        event = MESEvent(
            event_type="wip.unit.completed",
            source="wip",
            payload={
                "unit_id": str(unit_id),
                "step_id": str(step_id),
                "result": "pass",
            },
        )

        mock_unit = MagicMock()
        mock_unit.serial_number = "SN-001"
        mock_unit.order_id = _uuid()

        mock_order = MagicMock()
        mock_order.erp_reference = "ERP-99999"

        mock_step = MagicMock()
        mock_step.erp_operation_number = "0020"

        mock_session = AsyncMock()
        results = []
        for obj in [mock_unit, mock_order, mock_step]:
            r = MagicMock()
            r.scalar_one_or_none.return_value = obj
            results.append(r)
        mock_session.execute = AsyncMock(side_effect=results)
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("mes.adapters.erp.handlers.async_session_factory", return_value=mock_ctx):
            with patch("mes.adapters.erp.queue.ERPOutboundQueueService.enqueue", new_callable=AsyncMock) as mock_enqueue:
                await on_unit_completed_erp_report(event)

                mock_enqueue.assert_awaited_once()
                payload = mock_enqueue.call_args.kwargs.get("payload") or mock_enqueue.call_args[0][2]
                assert payload["qty_good"] == 1
                assert payload["qty_reject"] == 0
                assert payload["serial_number"] == "SN-001"

    @pytest.mark.asyncio
    async def test_handler_enqueues_fail_report(self):
        from mes.adapters.erp.handlers import on_unit_completed_erp_report
        from mes.framework.events.schema import MESEvent

        event = MESEvent(
            event_type="wip.unit.completed",
            source="wip",
            payload={
                "unit_id": str(_uuid()),
                "step_id": str(_uuid()),
                "result": "fail",
            },
        )

        mock_unit = MagicMock()
        mock_unit.serial_number = "SN-FAIL"
        mock_unit.order_id = _uuid()

        mock_order = MagicMock()
        mock_order.erp_reference = "ERP-FAIL"

        mock_step = MagicMock()
        mock_step.erp_operation_number = "0010"

        mock_session = AsyncMock()
        results = []
        for obj in [mock_unit, mock_order, mock_step]:
            r = MagicMock()
            r.scalar_one_or_none.return_value = obj
            results.append(r)
        mock_session.execute = AsyncMock(side_effect=results)
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("mes.adapters.erp.handlers.async_session_factory", return_value=mock_ctx):
            with patch("mes.adapters.erp.queue.ERPOutboundQueueService.enqueue", new_callable=AsyncMock) as mock_enqueue:
                await on_unit_completed_erp_report(event)

                payload = mock_enqueue.call_args.kwargs.get("payload") or mock_enqueue.call_args[0][2]
                assert payload["qty_good"] == 0
                assert payload["qty_reject"] == 1

    @pytest.mark.asyncio
    async def test_handler_skips_when_no_erp_reference(self):
        from mes.adapters.erp.handlers import on_unit_completed_erp_report
        from mes.framework.events.schema import MESEvent

        event = MESEvent(
            event_type="wip.unit.completed",
            source="wip",
            payload={
                "unit_id": str(_uuid()),
                "step_id": str(_uuid()),
                "result": "pass",
            },
        )

        mock_unit = MagicMock()
        mock_unit.order_id = _uuid()

        mock_order = MagicMock()
        mock_order.erp_reference = None  # No ERP link

        mock_session = AsyncMock()
        results = []
        for obj in [mock_unit, mock_order]:
            r = MagicMock()
            r.scalar_one_or_none.return_value = obj
            results.append(r)
        mock_session.execute = AsyncMock(side_effect=results)
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("mes.adapters.erp.handlers.async_session_factory", return_value=mock_ctx):
            with patch("mes.adapters.erp.queue.ERPOutboundQueueService.enqueue", new_callable=AsyncMock) as mock_enqueue:
                await on_unit_completed_erp_report(event)

                mock_enqueue.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════════
# 10. FULL LIFECYCLE SEQUENCE (integration-style with mocks)
# ═══════════════════════════════════════════════════════════════════

class TestFullUnitLifecycleSequence:
    """Verifies the complete happy-path event sequence for a unit."""

    @pytest.mark.asyncio
    async def test_lifecycle_event_sequence(self):
        """Track all events published during: create → start → complete → move(final)."""
        published_events: list = []

        async def capture_event(event):
            published_events.append(event.event_type)

        with patch("mes.core.wip.service.event_bus.publish", side_effect=capture_event):
            with patch("mes.core.wip.service.OperationsRequestService.start_order", new_callable=AsyncMock):
                # 1. Create
                session = _session_returning(None)
                await UnitService.create_unit(
                    session, serial_number="SN-SEQ-001", order_id=_uuid(),
                    product_id=_uuid(),
                )

            with patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock) as mock_get:
                unit_mock = _make_unit(status="queued", current_step_id=_uuid())
                mock_get.return_value = unit_mock
                session = AsyncMock()
                session.flush = AsyncMock()

                # 2. Start
                await UnitService.start_unit(session, unit_mock.id)

            with patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock) as mock_get:
                unit_mock.status = "in_process"
                mock_get.return_value = unit_mock
                history = _make_history()
                session = _session_returning(history)

                # 3. Complete step
                await UnitService.complete_unit_step(session, unit_mock.id, result="pass")

            with patch("mes.core.wip.service.UnitService.get_unit", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = unit_mock
                session = _session_returning(None)

                with patch("mes.core.wip.service.OperationsRequestService.increment_completed", new_callable=AsyncMock):
                    with patch(
                        "mes.core.routing.service.RoutingEngineService.get_next_step",
                        new_callable=AsyncMock, return_value=None,
                    ):
                        # 4. Move (final → completes unit)
                        await UnitService.move_unit(session, unit_mock.id)

        assert published_events == [
            "wip.unit.created",
            "wip.unit.started",
            "wip.unit.completed",
            "wip.unit.moved",
        ]
