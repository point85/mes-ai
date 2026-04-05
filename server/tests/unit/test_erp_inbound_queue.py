"""
Unit tests for the ERP Inbound Order Queue.

Covers:
- ERPInboundOrder model instantiation & field defaults
- Pydantic schema validation (InboundOrderRead, InboundQueueStats)
- Event factory functions
- OrderProcessor interface contract
- ERPInboundQueueService: enqueue, enqueue_from_sync, process_queue, retry
- CPGLotProcessor and ElectronicsUnitProcessor logic
"""

from __future__ import annotations

import json
import types
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mes.adapters.erp.inbound_queue import (
    ERPInboundOrder,
    ERPInboundQueueService,
    InboundOrderRead,
    InboundQueueStats,
    OrderProcessor,
    ProcessorResult,
    QUEUE_STATUSES,
    erp_inbound_failed,
    erp_inbound_processed,
)


# ═══════════════════════════════════════════════════════════════════
# 1. MODEL
# ═══════════════════════════════════════════════════════════════════


class TestERPInboundOrderModel:
    """Verify SQLAlchemy model field defaults and table name."""

    def test_table_name(self):
        assert ERPInboundOrder.__tablename__ == "erp_inbound_orders"

    def test_columns_exist(self):
        cols = {c.name for c in ERPInboundOrder.__table__.columns}
        expected = {
            "id", "erp_reference", "product_code", "payload",
            "status", "order_id", "wip_ids", "processor_name",
            "attempts", "max_attempts", "next_retry_at", "last_error",
            "processed_at", "created_at", "updated_at", "is_active",
        }
        assert expected.issubset(cols)

    def test_status_index(self):
        col = ERPInboundOrder.__table__.columns["status"]
        assert col.index is True

    def test_erp_reference_index(self):
        col = ERPInboundOrder.__table__.columns["erp_reference"]
        assert col.index is True


# ═══════════════════════════════════════════════════════════════════
# 2. SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class TestInboundOrderRead:
    def test_minimal(self):
        now = datetime.now(timezone.utc)
        schema = InboundOrderRead(
            id=str(uuid.uuid4()),
            erp_reference="ERP-001",
            product_code="WIDGET-A",
            payload={"erp_reference": "ERP-001", "product_code": "WIDGET-A", "quantity_ordered": 10},
            status="pending",
            attempts=0,
            max_attempts=5,
            created_at=now,
            updated_at=now,
        )
        assert schema.status == "pending"
        assert schema.order_id is None
        assert schema.wip_ids is None

    def test_processed_with_wip(self):
        now = datetime.now(timezone.utc)
        schema = InboundOrderRead(
            id=str(uuid.uuid4()),
            erp_reference="ERP-002",
            product_code="WIDGET-B",
            payload={"erp_reference": "ERP-002", "product_code": "WIDGET-B", "quantity_ordered": 5},
            status="processed",
            order_id=str(uuid.uuid4()),
            wip_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
            processor_name="cpg-lot-processor",
            attempts=1,
            max_attempts=5,
            processed_at=now,
            created_at=now,
            updated_at=now,
        )
        assert schema.status == "processed"
        assert len(schema.wip_ids) == 2


class TestInboundQueueStats:
    def test_defaults(self):
        stats = InboundQueueStats()
        assert stats.pending == 0
        assert stats.total == 0

    def test_with_counts(self):
        stats = InboundQueueStats(pending=3, processed=10, failed=1, retry=2, total=16)
        assert stats.total == 16


class TestQueueStatuses:
    def test_all_present(self):
        assert "pending" in QUEUE_STATUSES
        assert "processed" in QUEUE_STATUSES
        assert "failed" in QUEUE_STATUSES
        assert "retry" in QUEUE_STATUSES


# ═══════════════════════════════════════════════════════════════════
# 3. EVENTS
# ═══════════════════════════════════════════════════════════════════


class TestInboundEvents:
    def test_processed_event(self):
        evt = erp_inbound_processed("q-1", "ERP-001", "order-1")
        assert evt.event_type == "erp.inbound.processed"
        assert evt.payload["erp_reference"] == "ERP-001"
        assert evt.payload["order_id"] == "order-1"

    def test_failed_event(self):
        evt = erp_inbound_failed("q-2", "ERP-002", "timeout", 5)
        assert evt.event_type == "erp.inbound.failed"
        assert evt.payload["attempts"] == 5


# ═══════════════════════════════════════════════════════════════════
# 4. PROCESSOR INTERFACE
# ═══════════════════════════════════════════════════════════════════


class TestOrderProcessorInterface:
    """Ensure OrderProcessor is abstract and cannot be instantiated."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            OrderProcessor()

    def test_subclass_must_implement_name_and_process_order(self):
        class IncompleteProcessor(OrderProcessor):
            pass

        with pytest.raises(TypeError):
            IncompleteProcessor()


class TestProcessorResult:
    def test_minimal(self):
        r = ProcessorResult(order_id="abc-123")
        assert r.order_id == "abc-123"
        assert r.wip_ids == []

    def test_with_wip(self):
        r = ProcessorResult(order_id="abc-123", wip_ids=["u1", "u2"])
        assert len(r.wip_ids) == 2


# ═══════════════════════════════════════════════════════════════════
# 5. SERVICE — enqueue
# ═══════════════════════════════════════════════════════════════════


class TestERPInboundQueueServiceEnqueue:
    @pytest.mark.asyncio
    async def test_enqueue_creates_item(self):
        """enqueue() should add an ERPInboundOrder and flush."""
        session = AsyncMock()
        item_holder = []

        def capture_add(item):
            item.id = uuid.uuid4()
            item_holder.append(item)

        session.add = capture_add
        session.flush = AsyncMock()

        payload = {
            "erp_reference": "ERP-001",
            "product_code": "WIDGET-A",
            "quantity_ordered": 100,
        }
        result = await ERPInboundQueueService.enqueue(session, payload)

        assert result is not None
        assert len(item_holder) == 1
        item = item_holder[0]
        assert item.erp_reference == "ERP-001"
        assert item.product_code == "WIDGET-A"
        assert item.status == "pending"
        assert json.loads(item.payload)["quantity_ordered"] == 100


# ═══════════════════════════════════════════════════════════════════
# 6. SERVICE — enqueue_from_sync (dedup)
# ═══════════════════════════════════════════════════════════════════


class TestERPInboundQueueServiceEnqueueFromSync:
    @pytest.mark.asyncio
    async def test_skips_already_queued(self):
        """enqueue_from_sync() should skip orders whose erp_reference is already pending."""
        session = AsyncMock()

        # Simulate that ERP-001 is already in queue
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.uuid4()
        session.execute = AsyncMock(return_value=mock_result)

        dto = MagicMock()
        dto.model_dump.return_value = {
            "erp_reference": "ERP-001",
            "product_code": "WIDGET-A",
            "quantity_ordered": 50,
        }

        result = await ERPInboundQueueService.enqueue_from_sync(session, [dto])
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_enqueues_new_orders(self):
        """enqueue_from_sync() should enqueue orders not yet in queue."""
        session = AsyncMock()
        items_added = []

        # First call: check existing → None. Second call: flush after enqueue.
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result_none)

        def capture_add(item):
            item.id = uuid.uuid4()
            items_added.append(item)

        session.add = capture_add

        dto = MagicMock()
        dto.model_dump.return_value = {
            "erp_reference": "ERP-NEW-001",
            "product_code": "GADGET-X",
            "quantity_ordered": 25,
        }

        result = await ERPInboundQueueService.enqueue_from_sync(session, [dto])
        assert len(result) == 1
        assert len(items_added) == 1
        assert items_added[0].erp_reference == "ERP-NEW-001"


# ═══════════════════════════════════════════════════════════════════
# 7. SERVICE — set_processor / get_processor
# ═══════════════════════════════════════════════════════════════════


class _DummyProcessor(OrderProcessor):
    @property
    def name(self) -> str:
        return "dummy"

    async def process_order(self, session, payload):
        return ProcessorResult(order_id="test-id")


class TestProcessorRegistration:
    def test_set_and_get(self):
        original = ERPInboundQueueService._processor
        try:
            proc = _DummyProcessor()
            ERPInboundQueueService.set_processor(proc)
            assert ERPInboundQueueService.get_processor() is proc
            assert ERPInboundQueueService.get_processor().name == "dummy"
        finally:
            ERPInboundQueueService._processor = original

    def test_no_processor_returns_none(self):
        original = ERPInboundQueueService._processor
        try:
            ERPInboundQueueService._processor = None
            assert ERPInboundQueueService.get_processor() is None
        finally:
            ERPInboundQueueService._processor = original


# ═══════════════════════════════════════════════════════════════════
# 8. SERVICE — process_queue
# ═══════════════════════════════════════════════════════════════════


class TestERPInboundQueueServiceProcessQueue:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_processor(self):
        """process_queue() with no processor registered should return 0."""
        original = ERPInboundQueueService._processor
        try:
            ERPInboundQueueService._processor = None
            session = AsyncMock()
            result = await ERPInboundQueueService.process_queue(session)
            assert result == 0
        finally:
            ERPInboundQueueService._processor = original

    @pytest.mark.asyncio
    async def test_processes_pending_item(self):
        """process_queue() should call the processor and mark item as processed."""
        original = ERPInboundQueueService._processor
        try:
            proc = _DummyProcessor()
            ERPInboundQueueService.set_processor(proc)

            # Create a mock pending item
            item = MagicMock()
            item.id = uuid.uuid4()
            item.erp_reference = "ERP-010"
            item.payload = json.dumps({"erp_reference": "ERP-010", "product_code": "X", "quantity_ordered": 1})
            item.status = "pending"
            item.attempts = 0
            item.max_attempts = 5

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [item]

            session = AsyncMock()
            session.execute = AsyncMock(return_value=mock_result)

            with patch.object(proc, "process_order", new_callable=AsyncMock) as mock_process:
                mock_process.return_value = ProcessorResult(order_id="order-1", wip_ids=["lot-1"])

                # Patch event_bus.publish to avoid side effects
                with patch("mes.adapters.erp.inbound_queue.event_bus") as mock_bus:
                    mock_bus.publish = AsyncMock()
                    count = await ERPInboundQueueService.process_queue(session)

            assert count == 1
            assert item.status == "processed"
            assert item.order_id == "order-1"
            assert item.processor_name == "dummy"

        finally:
            ERPInboundQueueService._processor = original

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """process_queue() should set status='retry' on processor exception."""
        original = ERPInboundQueueService._processor
        try:
            proc = _DummyProcessor()
            ERPInboundQueueService.set_processor(proc)

            item = MagicMock()
            item.id = uuid.uuid4()
            item.erp_reference = "ERP-FAIL"
            item.payload = json.dumps({"erp_reference": "ERP-FAIL", "product_code": "Y", "quantity_ordered": 1})
            item.status = "pending"
            item.attempts = 0
            item.max_attempts = 5

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [item]

            session = AsyncMock()
            session.execute = AsyncMock(return_value=mock_result)

            with patch.object(proc, "process_order", new_callable=AsyncMock) as mock_process:
                mock_process.side_effect = ValueError("Product not found")

                with patch("mes.adapters.erp.inbound_queue.event_bus") as mock_bus:
                    mock_bus.publish = AsyncMock()
                    count = await ERPInboundQueueService.process_queue(session)

            assert count == 0
            assert item.status == "retry"
            assert item.attempts == 1
            assert "Product not found" in item.last_error
            assert item.next_retry_at is not None

        finally:
            ERPInboundQueueService._processor = original

    @pytest.mark.asyncio
    async def test_marks_failed_after_max_attempts(self):
        """process_queue() should mark item 'failed' when attempts >= max_attempts."""
        original = ERPInboundQueueService._processor
        try:
            proc = _DummyProcessor()
            ERPInboundQueueService.set_processor(proc)

            item = MagicMock()
            item.id = uuid.uuid4()
            item.erp_reference = "ERP-EXHAUST"
            item.payload = json.dumps({"erp_reference": "ERP-EXHAUST", "product_code": "Z", "quantity_ordered": 1})
            item.status = "retry"
            item.attempts = 4  # will become 5 (== max_attempts)
            item.max_attempts = 5

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [item]

            session = AsyncMock()
            session.execute = AsyncMock(return_value=mock_result)

            with patch.object(proc, "process_order", new_callable=AsyncMock) as mock_process:
                mock_process.side_effect = RuntimeError("Persistent failure")

                with patch("mes.adapters.erp.inbound_queue.event_bus") as mock_bus:
                    mock_bus.publish = AsyncMock()
                    count = await ERPInboundQueueService.process_queue(session)

            assert count == 0
            assert item.status == "failed"
            assert item.attempts == 5

        finally:
            ERPInboundQueueService._processor = original


# ═══════════════════════════════════════════════════════════════════
# 9. DEMO PROCESSORS — CPGLotProcessor
# ═══════════════════════════════════════════════════════════════════


class TestCPGLotProcessor:
    def test_name(self):
        from mes.core.demo.order_processors import CPGLotProcessor
        proc = CPGLotProcessor()
        assert proc.name == "cpg-lot-processor"

    def test_is_order_processor(self):
        from mes.core.demo.order_processors import CPGLotProcessor
        proc = CPGLotProcessor()
        assert isinstance(proc, OrderProcessor)

    @pytest.mark.asyncio
    async def test_creates_order_and_lot(self):
        """CPGLotProcessor should create a production order, release it, and create one lot."""
        from mes.core.demo.order_processors import CPGLotProcessor

        proc = CPGLotProcessor()
        session = AsyncMock()

        product_id = uuid.uuid4()
        route_id = uuid.uuid4()
        order_id = uuid.uuid4()
        lot_id = uuid.uuid4()

        # Mock _find_existing_order → None
        mock_no_existing = MagicMock()
        mock_no_existing.scalar_one_or_none.return_value = None

        # Mock _resolve_product → product
        product = types.SimpleNamespace(id=product_id, code="FG-OJ-1L")
        mock_product = MagicMock()
        mock_product.scalar_one_or_none.return_value = product

        # Mock _resolve_route → route
        route = types.SimpleNamespace(id=route_id)
        mock_route = MagicMock()
        mock_route.scalar_one_or_none.return_value = route

        # Return different results for sequential session.execute calls
        session.execute = AsyncMock(side_effect=[
            mock_no_existing,  # _find_existing_order
            mock_product,      # _resolve_product
            mock_route,        # _resolve_route
        ])

        order = types.SimpleNamespace(id=order_id, order_number="ERP-CPG-001", status="created")
        lot = types.SimpleNamespace(id=lot_id, lot_number="LOT-ERP-CPG-001")

        with patch("mes.core.demo.order_processors.ProductionOrderService") as mock_pos:
            mock_pos.create_order = AsyncMock(return_value=order)
            mock_pos.release_order = AsyncMock(return_value=order)
            with patch("mes.core.demo.order_processors.LotService") as mock_ls:
                mock_ls.create_lot = AsyncMock(return_value=lot)

                result = await proc.process_order(session, {
                    "erp_reference": "ERP-CPG-001",
                    "product_code": "FG-OJ-1L",
                    "quantity_ordered": 1000,
                    "priority": 2,
                })

        assert result.order_id == str(order_id)
        assert len(result.wip_ids) == 1
        assert str(lot_id) in result.wip_ids
        mock_pos.create_order.assert_awaited_once()
        mock_pos.release_order.assert_awaited_once()
        mock_ls.create_lot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_skips_existing_order(self):
        """CPGLotProcessor should return existing order and not create duplicates."""
        from mes.core.demo.order_processors import CPGLotProcessor

        proc = CPGLotProcessor()
        session = AsyncMock()

        existing_id = uuid.uuid4()
        existing_order = types.SimpleNamespace(id=existing_id, order_number="ERP-DUP")

        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = existing_order
        session.execute = AsyncMock(return_value=mock_existing)

        result = await proc.process_order(session, {
            "erp_reference": "ERP-DUP",
            "product_code": "FG-OJ-1L",
            "quantity_ordered": 500,
        })

        assert result.order_id == str(existing_id)
        assert result.wip_ids == []


# ═══════════════════════════════════════════════════════════════════
# 10. DEMO PROCESSORS — ElectronicsUnitProcessor
# ═══════════════════════════════════════════════════════════════════


class TestElectronicsUnitProcessor:
    def test_name(self):
        from mes.core.demo.order_processors import ElectronicsUnitProcessor
        proc = ElectronicsUnitProcessor()
        assert proc.name == "electronics-unit-processor"

    def test_is_order_processor(self):
        from mes.core.demo.order_processors import ElectronicsUnitProcessor
        proc = ElectronicsUnitProcessor()
        assert isinstance(proc, OrderProcessor)

    @pytest.mark.asyncio
    async def test_creates_order_and_units(self):
        """ElectronicsUnitProcessor should create order + N units."""
        from mes.core.demo.order_processors import ElectronicsUnitProcessor

        proc = ElectronicsUnitProcessor()
        session = AsyncMock()

        product_id = uuid.uuid4()
        route_id = uuid.uuid4()
        order_id = uuid.uuid4()

        mock_no_existing = MagicMock()
        mock_no_existing.scalar_one_or_none.return_value = None

        product = types.SimpleNamespace(id=product_id, code="ECB-100")
        mock_product = MagicMock()
        mock_product.scalar_one_or_none.return_value = product

        route = types.SimpleNamespace(id=route_id)
        mock_route = MagicMock()
        mock_route.scalar_one_or_none.return_value = route

        session.execute = AsyncMock(side_effect=[
            mock_no_existing,
            mock_product,
            mock_route,
        ])

        order = types.SimpleNamespace(id=order_id, order_number="ERP-ECB-001", status="created")

        unit_counter = [0]

        async def mock_create_unit(session, **kwargs):
            unit_counter[0] += 1
            return types.SimpleNamespace(
                id=uuid.uuid4(),
                serial_number=kwargs["serial_number"],
            )

        with patch("mes.core.demo.order_processors.ProductionOrderService") as mock_pos:
            mock_pos.create_order = AsyncMock(return_value=order)
            mock_pos.release_order = AsyncMock(return_value=order)
            with patch("mes.core.demo.order_processors.UnitService") as mock_us:
                mock_us.create_unit = mock_create_unit

                result = await proc.process_order(session, {
                    "erp_reference": "ERP-ECB-001",
                    "product_code": "ECB-100",
                    "quantity_ordered": 3,
                    "priority": 1,
                })

        assert result.order_id == str(order_id)
        assert len(result.wip_ids) == 3
        assert unit_counter[0] == 3
        mock_pos.create_order.assert_awaited_once()
        mock_pos.release_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_serial_number_format(self):
        """ElectronicsUnitProcessor serial numbers should follow SN-{ref}-NNNNN pattern."""
        from mes.core.demo.order_processors import ElectronicsUnitProcessor

        proc = ElectronicsUnitProcessor()
        session = AsyncMock()

        product_id = uuid.uuid4()
        order_id = uuid.uuid4()

        mock_no_existing = MagicMock()
        mock_no_existing.scalar_one_or_none.return_value = None

        product = types.SimpleNamespace(id=product_id, code="ECB-100")
        mock_product = MagicMock()
        mock_product.scalar_one_or_none.return_value = product

        mock_route = MagicMock()
        mock_route.scalar_one_or_none.return_value = None  # no route

        session.execute = AsyncMock(side_effect=[
            mock_no_existing, mock_product, mock_route,
        ])

        order = types.SimpleNamespace(id=order_id, order_number="ERP-SN-TEST", status="created")
        captured_serials: list[str] = []

        async def mock_create_unit(session, **kwargs):
            captured_serials.append(kwargs["serial_number"])
            return types.SimpleNamespace(id=uuid.uuid4(), serial_number=kwargs["serial_number"])

        with patch("mes.core.demo.order_processors.ProductionOrderService") as mock_pos:
            mock_pos.create_order = AsyncMock(return_value=order)
            mock_pos.release_order = AsyncMock(return_value=order)
            with patch("mes.core.demo.order_processors.UnitService") as mock_us:
                mock_us.create_unit = mock_create_unit

                await proc.process_order(session, {
                    "erp_reference": "ERP-SN-TEST",
                    "product_code": "ECB-100",
                    "quantity_ordered": 2,
                })

        assert captured_serials == ["SN-ERP-SN-TEST-00001", "SN-ERP-SN-TEST-00002"]


# ═══════════════════════════════════════════════════════════════════
# 11. MAIN.PY — processor registration
# ═══════════════════════════════════════════════════════════════════


class TestDemoProcessorRegistration:
    """Verify _register_demo_order_processor wires the correct processor."""

    def test_register_cpg(self):
        """ERP_ORDER_PROCESSOR=cpg should register CPGLotProcessor."""
        from mes.core.demo.order_processors import CPGLotProcessor
        original = ERPInboundQueueService._processor
        try:
            with patch.dict("os.environ", {"ERP_ORDER_PROCESSOR": "cpg"}):
                from mes.main import _register_demo_order_processor
                _register_demo_order_processor()
                proc = ERPInboundQueueService.get_processor()
                assert isinstance(proc, CPGLotProcessor)
        finally:
            ERPInboundQueueService._processor = original

    def test_register_electronics(self):
        """ERP_ORDER_PROCESSOR=electronics should register ElectronicsUnitProcessor."""
        from mes.core.demo.order_processors import ElectronicsUnitProcessor
        original = ERPInboundQueueService._processor
        try:
            with patch.dict("os.environ", {"ERP_ORDER_PROCESSOR": "electronics"}):
                from mes.main import _register_demo_order_processor
                _register_demo_order_processor()
                proc = ERPInboundQueueService.get_processor()
                assert isinstance(proc, ElectronicsUnitProcessor)
        finally:
            ERPInboundQueueService._processor = original

    def test_register_none(self):
        """ERP_ORDER_PROCESSOR=none should leave no processor registered."""
        original = ERPInboundQueueService._processor
        try:
            ERPInboundQueueService._processor = None
            with patch.dict("os.environ", {"ERP_ORDER_PROCESSOR": "none"}):
                from mes.main import _register_demo_order_processor
                _register_demo_order_processor()
                assert ERPInboundQueueService.get_processor() is None
        finally:
            ERPInboundQueueService._processor = original

    def test_default_is_cpg(self):
        """No ERP_ORDER_PROCESSOR env var should default to CPG."""
        from mes.core.demo.order_processors import CPGLotProcessor
        original = ERPInboundQueueService._processor
        try:
            with patch.dict("os.environ", {}, clear=False):
                import os
                os.environ.pop("ERP_ORDER_PROCESSOR", None)
                from mes.main import _register_demo_order_processor
                _register_demo_order_processor()
                proc = ERPInboundQueueService.get_processor()
                assert isinstance(proc, CPGLotProcessor)
        finally:
            ERPInboundQueueService._processor = original


# ═══════════════════════════════════════════════════════════════════
# 12. _parse_dt HELPER
# ═══════════════════════════════════════════════════════════════════


class TestParseDt:
    """Tests for the datetime parsing helper used by order processors."""

    def test_none_returns_none(self):
        from mes.core.demo.order_processors import _parse_dt
        assert _parse_dt(None) is None

    def test_string_iso(self):
        from mes.core.demo.order_processors import _parse_dt
        result = _parse_dt("2026-04-06T08:00:00")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 6

    def test_datetime_passthrough(self):
        from mes.core.demo.order_processors import _parse_dt
        now = datetime.now(timezone.utc)
        assert _parse_dt(now) is now

    def test_string_with_timezone(self):
        from mes.core.demo.order_processors import _parse_dt
        result = _parse_dt("2026-04-06T08:00:00+00:00")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


# ═══════════════════════════════════════════════════════════════════
# 13. PUSH ENDPOINT SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class TestInboundOrderPayload:
    """Tests for the direct push endpoint request schemas."""

    def test_payload_required_fields(self):
        from mes.adapters.erp.routes import InboundOrderPayload
        payload = InboundOrderPayload(
            erp_reference="TEST-001",
            product_code="FG-OJ-1L",
            quantity_ordered=100,
        )
        assert payload.erp_reference == "TEST-001"
        assert payload.priority == 0
        assert payload.planned_start is None

    def test_payload_all_fields(self):
        from mes.adapters.erp.routes import InboundOrderPayload
        payload = InboundOrderPayload(
            erp_reference="TEST-002",
            product_code="FG-OJ-1L",
            quantity_ordered=500,
            priority=5,
            planned_start="2026-04-06T08:00:00",
            planned_end="2026-04-06T16:00:00",
            uom="EA",
            metadata={"source": "test"},
        )
        assert payload.quantity_ordered == 500
        assert payload.uom == "EA"

    def test_batch_schema(self):
        from mes.adapters.erp.routes import InboundOrderBatch
        batch = InboundOrderBatch(orders=[
            {"erp_reference": "A", "product_code": "P1", "quantity_ordered": 10},
            {"erp_reference": "B", "product_code": "P2", "quantity_ordered": 20},
        ])
        assert len(batch.orders) == 2
