"""
Unit tests for the complete production lot lifecycle — service-layer execution.

Covers every stage from lot creation through order closing:
  1. Lot creation          — LotService.create_lot
  2. Lot start             — LotService.start_lot (queued → in_process)
  3. Lot step completion   — LotService.complete_lot_step (history close, scrap→order)
  4. Lot move              — LotService.move_lot (next step / final-step completion)
  5. Lot hold / release    — LotService.hold_lot, release_hold_lot
  6. Lot scrap             — LotService.scrap_lot (status + order increment)
  7. Order lifecycle        — increment_completed, increment_scrapped, complete, close
  8. Data collection       — DataPointService.collect (persist + event)
  9. Quality test result   — TestResultService.record_result (persist + event)
 10. ERP outbound handler  — on_lot_completed_erp_report (enqueue)
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Register all SQLAlchemy models so mapper relationships resolve correctly.
# Without these, lazy relationship strings (e.g. "ProductDefinition") fail to resolve.
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

from mes.core.wip.service import LotService
from mes.core.wip.exceptions import (
    DuplicateLotNumberException,
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


def _make_lot(**overrides) -> MagicMock:
    """Create a MagicMock behaving like a Lot ORM instance."""
    defaults = dict(
        id=_uuid(), lot_number="LOT-001", order_id=_uuid(), product_id=_uuid(),
        quantity=1000, current_step_id=_uuid(), current_equipment_id=None,
        status="queued", is_active=True,
        created_at=_now(), updated_at=_now(),
    )
    defaults.update(overrides)
    lot = MagicMock()
    lot.configure_mock(**defaults)
    return lot


def _make_order(**overrides) -> MagicMock:
    defaults = dict(
        id=_uuid(), order_number="ORD-001", status="in_progress",
        quantity_ordered=1000, quantity_completed=0, quantity_scrapped=0,
        actual_end=None,
    )
    defaults.update(overrides)
    order = MagicMock()
    order.configure_mock(**defaults)
    return order


def _make_history(**overrides) -> MagicMock:
    defaults = dict(
        id=_uuid(), lot_id=_uuid(), step_id=_uuid(), equipment_id=None,
        entered_at=_now(), exited_at=None,
        quantity_in=1000, quantity_out=0, quantity_scrapped=0,
        operator_id=None,
    )
    defaults.update(overrides)
    hist = MagicMock()
    hist.configure_mock(**defaults)
    return hist


def _make_step(**overrides) -> MagicMock:
    defaults = dict(
        id=_uuid(), route_id=_uuid(), name="Blending",
        sequence=10, step_type="production",
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
# 1. LOT CREATION
# ═══════════════════════════════════════════════════════════════════

class TestLotCreation:
    """LotService.create_lot — persist, auto-start order, publish event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.start_order", new_callable=AsyncMock)
    async def test_creates_lot_and_fires_event(self, mock_start_order, mock_publish):
        session = _session_returning(None)  # no duplicate
        lot_data = dict(
            lot_number="LOT-NEW", order_id=_uuid(), product_id=_uuid(), quantity=500,
        )
        lot = await LotService.create_lot(session, **lot_data)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        mock_start_order.assert_awaited_once()
        mock_publish.assert_awaited_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.created"
        assert event.payload["lot_number"] == "LOT-NEW"
        assert event.payload["quantity"] == 500

    @pytest.mark.asyncio
    async def test_rejects_duplicate_lot_number(self):
        existing_lot = _make_lot(lot_number="LOT-DUP")
        session = _session_returning(existing_lot)

        with pytest.raises(DuplicateLotNumberException):
            await LotService.create_lot(
                session, lot_number="LOT-DUP", order_id=_uuid(),
                product_id=_uuid(), quantity=100,
            )


# ═══════════════════════════════════════════════════════════════════
# 2. LOT START
# ═══════════════════════════════════════════════════════════════════

class TestLotStart:
    """LotService.start_lot — status transition, history creation, event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_start_transitions_to_in_process(self, mock_get, mock_publish):
        lot = _make_lot(status="queued", current_step_id=_uuid())
        mock_get.return_value = lot
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await LotService.start_lot(session, lot.id)

        assert result.status == "in_process"
        session.add.assert_called_once()        # history record
        session.flush.assert_awaited()
        mock_publish.assert_awaited_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.started"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_start_rejects_completed_lot(self, mock_get):
        lot = _make_lot(status="completed")
        mock_get.return_value = lot
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await LotService.start_lot(session, lot.id)

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_start_resolves_first_step_if_none(self, mock_get, mock_publish):
        lot = _make_lot(status="queued", current_step_id=None)
        mock_get.return_value = lot
        first_step = _make_step(sequence=10)
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch(
            "mes.core.routing.service.RoutingEngineService.get_first_step",
            new_callable=AsyncMock, return_value=first_step,
        ) as mock_first:
            await LotService.start_lot(session, lot.id)
            mock_first.assert_awaited_once()
            assert lot.current_step_id == first_step.id


# ═══════════════════════════════════════════════════════════════════
# 3. LOT STEP COMPLETION
# ═══════════════════════════════════════════════════════════════════

class TestLotStepCompletion:
    """LotService.complete_lot_step — history close, qty update, scrap→order."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_scrapped", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_complete_step_updates_history_and_qty(
        self, mock_get, mock_incr_scrap, mock_publish,
    ):
        step_id = _uuid()
        lot = _make_lot(status="in_process", current_step_id=step_id, quantity=1000)
        mock_get.return_value = lot
        history = _make_history(lot_id=lot.id, step_id=step_id)
        session = _session_returning(history)

        result = await LotService.complete_lot_step(session, lot.id, quantity_out=998, quantity_scrapped=2)

        # History record closed
        assert history.exited_at is not None
        assert history.quantity_out == 998
        assert history.quantity_scrapped == 2
        # Lot quantity updated to output
        assert lot.quantity == 998
        # Scrap propagated to order
        mock_incr_scrap.assert_awaited_once_with(session, lot.order_id, 2)
        # Event published
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.completed"
        assert event.payload["quantity_out"] == 998
        assert event.payload["quantity_scrapped"] == 2

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_scrapped", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_complete_step_zero_scrap_no_order_update(
        self, mock_get, mock_incr_scrap, mock_publish,
    ):
        lot = _make_lot(status="in_process", quantity=500)
        mock_get.return_value = lot
        history = _make_history()
        session = _session_returning(history)

        await LotService.complete_lot_step(session, lot.id, quantity_out=500, quantity_scrapped=0)

        mock_incr_scrap.assert_not_awaited()
        assert lot.quantity == 500

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_scrapped", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_complete_step_defaults_qty_out(
        self, mock_get, mock_incr_scrap, mock_publish,
    ):
        """When quantity_out is None, it defaults to lot.quantity - quantity_scrapped."""
        lot = _make_lot(status="in_process", quantity=1000)
        mock_get.return_value = lot
        history = _make_history()
        session = _session_returning(history)

        await LotService.complete_lot_step(session, lot.id, quantity_scrapped=5)

        assert lot.quantity == 995  # 1000 - 5
        event = mock_publish.call_args[0][0]
        assert event.payload["quantity_out"] == 995

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_complete_step_rejects_queued_lot(self, mock_get):
        lot = _make_lot(status="queued")
        mock_get.return_value = lot
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await LotService.complete_lot_step(session, lot.id)


# ═══════════════════════════════════════════════════════════════════
# 4. LOT MOVE
# ═══════════════════════════════════════════════════════════════════

class TestLotMove:
    """LotService.move_lot — next-step routing, final-step completion."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_move_to_explicit_target_step(self, mock_get, mock_publish):
        from_step = _uuid()
        to_step = _uuid()
        lot = _make_lot(status="in_process", current_step_id=from_step)
        mock_get.return_value = lot
        session = _session_returning(None)  # no open history record to close

        result = await LotService.move_lot(session, lot.id, target_step_id=to_step)

        assert lot.current_step_id == to_step
        assert lot.status == "queued"
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.moved"
        assert event.payload["to_step_id"] == str(to_step)

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_completed", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_move_completes_lot_when_no_next_step(
        self, mock_get, mock_incr_complete, mock_publish,
    ):
        """When routing engine returns None → lot completes, order qty incremented."""
        from_step = _uuid()
        lot = _make_lot(status="in_process", current_step_id=from_step, quantity=998)
        mock_get.return_value = lot

        session = _session_returning(None)  # no history record for result inference

        with patch(
            "mes.core.routing.service.RoutingEngineService.get_next_step",
            new_callable=AsyncMock, return_value=None,
        ):
            result = await LotService.move_lot(session, lot.id)

        assert lot.status == "completed"
        assert lot.current_step_id is None
        assert lot.current_equipment_id is None
        mock_incr_complete.assert_awaited_once_with(session, lot.order_id, 998)
        event = mock_publish.call_args[0][0]
        assert event.payload["to_step_id"] is None

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_move_advances_to_routing_engine_next_step(self, mock_get, mock_publish):
        from_step = _uuid()
        next_step = _make_step(id=_uuid(), sequence=20, name="Pasteurization")
        lot = _make_lot(status="in_process", current_step_id=from_step)
        mock_get.return_value = lot

        session = _session_returning(None)  # no history

        with patch(
            "mes.core.routing.service.RoutingEngineService.get_next_step",
            new_callable=AsyncMock, return_value=next_step,
        ):
            result = await LotService.move_lot(session, lot.id)

        assert lot.current_step_id == next_step.id
        assert lot.status == "queued"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_move_rejects_completed_lot(self, mock_get):
        lot = _make_lot(status="completed")
        mock_get.return_value = lot
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await LotService.move_lot(session, lot.id)


# ═══════════════════════════════════════════════════════════════════
# 5. HOLD / RELEASE
# ═══════════════════════════════════════════════════════════════════

class TestLotHoldRelease:
    """LotService.hold_lot, release_hold_lot — status transitions & events."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_hold_sets_on_hold_and_fires_event(self, mock_get, mock_publish):
        lot = _make_lot(status="in_process")
        mock_get.return_value = lot
        session = AsyncMock()
        session.flush = AsyncMock()

        await LotService.hold_lot(session, lot.id, "Quality investigation")

        assert lot.status == "on_hold"
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.held"
        assert event.payload["reason"] == "Quality investigation"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_hold_rejects_completed_lot(self, mock_get):
        lot = _make_lot(status="completed")
        mock_get.return_value = lot
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await LotService.hold_lot(session, lot.id, "reason")

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_release_returns_to_queued(self, mock_get, mock_publish):
        lot = _make_lot(status="on_hold")
        mock_get.return_value = lot
        session = AsyncMock()
        session.flush = AsyncMock()

        await LotService.release_hold_lot(session, lot.id)

        assert lot.status == "queued"
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.released"

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_release_rejects_non_held_lot(self, mock_get):
        lot = _make_lot(status="in_process")
        mock_get.return_value = lot
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await LotService.release_hold_lot(session, lot.id)


# ═══════════════════════════════════════════════════════════════════
# 6. LOT SCRAP
# ═══════════════════════════════════════════════════════════════════

class TestLotScrap:
    """LotService.scrap_lot — status change, order qty update, event."""

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.wip.service.OperationsRequestService.increment_scrapped", new_callable=AsyncMock)
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_scrap_sets_status_and_increments_order(
        self, mock_get, mock_incr_scrap, mock_publish,
    ):
        step_id = _uuid()
        lot = _make_lot(status="in_process", current_step_id=step_id, quantity=500)
        mock_get.return_value = lot
        session = _session_returning(None)

        await LotService.scrap_lot(session, lot.id, "Contaminated")

        assert lot.status == "scrapped"
        assert lot.current_equipment_id is None
        mock_incr_scrap.assert_awaited_once_with(session, lot.order_id, 500)
        event = mock_publish.call_args[0][0]
        assert event.event_type == "wip.lot.scrapped"
        assert event.payload["reason"] == "Contaminated"
        assert event.payload["quantity"] == 500

    @pytest.mark.asyncio
    @patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock)
    async def test_scrap_rejects_already_scrapped(self, mock_get):
        lot = _make_lot(status="scrapped")
        mock_get.return_value = lot
        session = AsyncMock()

        with pytest.raises(InvalidWIPTransitionException):
            await LotService.scrap_lot(session, lot.id, "reason")


# ═══════════════════════════════════════════════════════════════════
# 7. ORDER LIFECYCLE — increment, complete, close
# ═══════════════════════════════════════════════════════════════════

class TestOrderLifecycle:
    """OperationsRequestService — increment_completed, increment_scrapped,
    complete_order, close_order."""

    @pytest.mark.asyncio
    @patch("mes.core.operations.service.OperationsRequestService.get_order", new_callable=AsyncMock)
    async def test_increment_completed(self, mock_get):
        order = _make_order(quantity_completed=0)
        mock_get.return_value = order
        session = AsyncMock()
        session.flush = AsyncMock()

        result = await OperationsRequestService.increment_completed(session, order.id, qty=100)

        assert order.quantity_completed == 100

    @pytest.mark.asyncio
    @patch("mes.core.operations.service.OperationsRequestService.get_order", new_callable=AsyncMock)
    async def test_increment_completed_accumulates(self, mock_get):
        order = _make_order(quantity_completed=200)
        mock_get.return_value = order
        session = AsyncMock()
        session.flush = AsyncMock()

        await OperationsRequestService.increment_completed(session, order.id, qty=50)

        assert order.quantity_completed == 250

    @pytest.mark.asyncio
    @patch("mes.core.operations.service.OperationsRequestService.get_order", new_callable=AsyncMock)
    async def test_increment_scrapped(self, mock_get):
        order = _make_order(quantity_scrapped=0)
        mock_get.return_value = order
        session = AsyncMock()
        session.flush = AsyncMock()

        await OperationsRequestService.increment_scrapped(session, order.id, qty=5)

        assert order.quantity_scrapped == 5

    @pytest.mark.asyncio
    @patch("mes.core.operations.service.event_bus.publish", new_callable=AsyncMock)
    @patch("mes.core.operations.service.OperationsRequestService.get_order", new_callable=AsyncMock)
    async def test_complete_order(self, mock_get, mock_publish):
        order = _make_order(status="in_progress", actual_end=None)
        mock_get.return_value = order
        session = AsyncMock()
        session.flush = AsyncMock()

        await OperationsRequestService.complete_order(session, order.id)

        assert order.status == "completed"
        assert order.actual_end is not None
        event = mock_publish.call_args[0][0]
        assert event.event_type == "operations.request.completed"

    @pytest.mark.asyncio
    @patch("mes.core.operations.service.OperationsRequestService.get_order", new_callable=AsyncMock)
    async def test_close_order(self, mock_get):
        order = _make_order(status="completed", actual_end=None)
        mock_get.return_value = order
        session = AsyncMock()
        session.flush = AsyncMock()

        await OperationsRequestService.close_order(session, order.id)

        assert order.status == "closed"
        assert order.actual_end is not None


# ═══════════════════════════════════════════════════════════════════
# 8. DATA COLLECTION — service execution
# ═══════════════════════════════════════════════════════════════════

class TestDataCollectionService:
    """DataPointService.collect — persist, validate, publish event."""

    @pytest.mark.asyncio
    async def test_collect_numeric_creates_data_point(self):
        from mes.core.data_collection.service import DataPointService

        defn = MagicMock()
        defn.id = _uuid()
        defn.code = "temperature"
        defn.data_type = "numeric"
        defn.is_required = False
        defn.lower_limit = 0.0
        defn.upper_limit = 100.0
        defn.enum_values = None

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("mes.core.data_collection.service.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            result = await DataPointService.collect(
                session, defn, lot_id=_uuid(), value_numeric=72.5,
            )

        session.add.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "data.collected"

    @pytest.mark.asyncio
    async def test_collect_rejects_out_of_range_numeric(self):
        from mes.core.data_collection.service import DataPointService
        from mes.core.data_collection.exceptions import ValueOutOfLimitsException

        defn = MagicMock()
        defn.id = _uuid()
        defn.code = "temperature"
        defn.data_type = "numeric"
        defn.is_required = False
        defn.lower_limit = 0.0
        defn.upper_limit = 100.0
        defn.enum_values = None

        session = AsyncMock()

        with pytest.raises(ValueOutOfLimitsException):
            await DataPointService.collect(
                session, defn, lot_id=_uuid(), value_numeric=150.0,
            )


# ═══════════════════════════════════════════════════════════════════
# 9. QUALITY TEST RESULT — service execution
# ═══════════════════════════════════════════════════════════════════

class TestQualityResultService:
    """TestResultService.record_result — persist, publish pass/fail event."""

    @pytest.mark.asyncio
    async def test_record_pass_result(self):
        from mes.core.quality.service import TestResultService

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("mes.core.quality.service.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            result = await TestResultService.record_result(
                session,
                test_id=_uuid(), lot_id=_uuid(),
                result="pass", tested_at=_now(),
            )

        session.add.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "quality.test.passed"

    @pytest.mark.asyncio
    async def test_record_fail_result(self):
        from mes.core.quality.service import TestResultService

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("mes.core.quality.service.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            result = await TestResultService.record_result(
                session,
                test_id=_uuid(), lot_id=_uuid(),
                result="fail", tested_at=_now(),
            )

        event = mock_publish.call_args[0][0]
        assert event.event_type == "quality.test.failed"


# ═══════════════════════════════════════════════════════════════════
# 10. ERP OUTBOUND — handler enqueue on lot completion
# ═══════════════════════════════════════════════════════════════════

class TestERPOutboundHandler:
    """on_lot_completed_erp_report — enqueues outbound report."""

    @pytest.mark.asyncio
    async def test_handler_enqueues_completion_report(self):
        from mes.adapters.erp.handlers import on_lot_completed_erp_report
        from mes.framework.events.schema import MESEvent

        lot_id = _uuid()
        step_id = _uuid()

        event = MESEvent(
            event_type="wip.lot.completed",
            source="wip",
            payload={
                "lot_id": str(lot_id),
                "step_id": str(step_id),
                "quantity_out": 998,
                "quantity_scrapped": 2,
            },
        )

        # Mock the DB session and the objects it returns
        mock_lot = MagicMock()
        mock_lot.lot_number = "LOT-001"
        mock_lot.order_id = _uuid()

        mock_order = MagicMock()
        mock_order.erp_reference = "ERP-12345"

        mock_step = MagicMock()
        mock_step.erp_operation_number = "0010"

        mock_session = AsyncMock()
        # get_lot, get_order, get_step — 3 sequential DB lookups
        results = []
        for obj in [mock_lot, mock_order, mock_step]:
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
                await on_lot_completed_erp_report(event)

                mock_enqueue.assert_awaited_once()
                call_args = mock_enqueue.call_args
                # enqueue(session, report_type="completion", payload={...})
                assert call_args.kwargs.get("report_type") or call_args[0][1] == "completion"
                payload = call_args.kwargs.get("payload") or call_args[0][2]
                assert payload["qty_good"] == 998
                assert payload["qty_reject"] == 2

    @pytest.mark.asyncio
    async def test_handler_skips_when_no_erp_reference(self):
        from mes.adapters.erp.handlers import on_lot_completed_erp_report
        from mes.framework.events.schema import MESEvent

        event = MESEvent(
            event_type="wip.lot.completed",
            source="wip",
            payload={
                "lot_id": str(_uuid()),
                "step_id": str(_uuid()),
                "quantity_out": 100,
                "quantity_scrapped": 0,
            },
        )

        mock_order = MagicMock()
        mock_order.erp_reference = None  # No ERP link

        mock_lot = MagicMock()
        mock_lot.order_id = _uuid()

        mock_session = AsyncMock()
        results = []
        for obj in [mock_lot, mock_order]:
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
                await on_lot_completed_erp_report(event)

                mock_enqueue.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════════
# 11. FULL LIFECYCLE SEQUENCE (integration-style with mocks)
# ═══════════════════════════════════════════════════════════════════

class TestFullLotLifecycleSequence:
    """Verifies the complete happy-path event sequence for a lot."""

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
                lot = await LotService.create_lot(
                    session, lot_number="LOT-SEQ-001", order_id=_uuid(),
                    product_id=_uuid(), quantity=100,
                )

            with patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock) as mock_get:
                lot_mock = _make_lot(status="queued", quantity=100, current_step_id=_uuid())
                mock_get.return_value = lot_mock
                session = AsyncMock()
                session.add = MagicMock()
                session.flush = AsyncMock()

                # 2. Start
                await LotService.start_lot(session, lot_mock.id)

            with patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock) as mock_get:
                lot_mock.status = "in_process"
                mock_get.return_value = lot_mock
                history = _make_history()
                session = _session_returning(history)

                # 3. Complete step
                await LotService.complete_lot_step(session, lot_mock.id, quantity_out=100, quantity_scrapped=0)

            with patch("mes.core.wip.service.LotService.get_lot", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = lot_mock
                session = _session_returning(None)  # no history for result

                with patch("mes.core.wip.service.OperationsRequestService.increment_completed", new_callable=AsyncMock):
                    with patch(
                        "mes.core.routing.service.RoutingEngineService.get_next_step",
                        new_callable=AsyncMock, return_value=None,
                    ):
                        # 4. Move (final → completes lot)
                        await LotService.move_lot(session, lot_mock.id)

        assert published_events == [
            "wip.lot.created",
            "wip.lot.started",
            "wip.lot.completed",
            "wip.lot.moved",
        ]  # no quality.nc.created when quantity_scrapped=0
