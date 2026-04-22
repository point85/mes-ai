"""
Unit tests for ERP integration adapters.

Covers:
- DTO construction and validation (inbound + outbound)
- MockERPInboundAdapter (fixture loading, transform layer)
- MockERPOutboundAdapter (report storage, doc numbering, ERPConfirmation)
- Exception construction and error codes
- Event factory functions for outbound queue
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.adapters.erp.dtos import (
    BillOfMaterialDTO,
    BOMItemDTO,
    CompletionReport,
    ConsumptionReport,
    DowntimeReport,
    ERPConfirmation,
    LaborReport,
    MaterialConsumptionDTO,
    MaterialDefinitionDTO,
    ProcessRouteDTO,
    ProductDefinitionDTO,
    OperationsRequestDTO,
    QualityResultReport,
    RouteStepDTO,
    ScrapReport,
    WorkCellDTO,
)
from mes.adapters.erp.exceptions import (
    ERPConnectionError,
    ERPOutboundError,
    ERPSyncError,
)
from mes.adapters.erp.mock_adapter import (
    MockERPInboundAdapter,
    MockERPOutboundAdapter,
    MockERPTransformLayer,
)
from mes.adapters.erp.queue import (
    QUEUE_STATUSES,
    REPORT_TYPES,
    QueueItemCreate,
    QueueItemRead,
    QueueStats,
    erp_outbound_failed,
    erp_outbound_sent,
)


# ═══════════════════════════════════════════════════════════════════
# Inbound DTOs
# ═══════════════════════════════════════════════════════════════════


class TestOperationsRequestDTO:
    def test_minimal(self):
        dto = OperationsRequestDTO(
            erp_reference="PO-001",
            product_code="WIDGET-A",
            quantity_ordered=100,
        )
        assert dto.priority == 500
        assert dto.uom == "EA"
        assert dto.metadata == {}

    def test_full(self):
        now = datetime.now(timezone.utc)
        dto = OperationsRequestDTO(
            erp_reference="PO-002",
            product_code="GADGET-X",
            quantity_ordered=50,
            planned_start=now,
            planned_end=now,
            priority=900,
            uom="KG",
            bom_id="BOM-1",
            routing_id="RT-1",
            metadata={"custom": "value"},
        )
        assert dto.priority == 900
        assert dto.bom_id == "BOM-1"

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            OperationsRequestDTO(
                erp_reference="PO-BAD",
                product_code="X",
                quantity_ordered=0,
            )


class TestMaterialDefinitionDTO:
    def test_defaults(self):
        dto = MaterialDefinitionDTO(code="MAT-01", name="Steel")
        assert dto.material_type == "raw"
        assert dto.uom == "EA"
        assert dto.shelf_life_days is None


class TestProductDefinitionDTO:
    def test_defaults(self):
        dto = ProductDefinitionDTO(code="PROD-01", name="Widget")
        assert dto.product_type == "discrete"
        assert dto.version == "1.0"


class TestBOMDTOs:
    def test_bom_with_items(self):
        bom = BillOfMaterialDTO(
            product_code="WIDGET-A",
            items=[
                BOMItemDTO(material_code="STEEL", quantity=2.5),
                BOMItemDTO(material_code="SCREW", quantity=10, uom="PC"),
            ],
        )
        assert len(bom.items) == 2
        assert bom.items[0].sequence == 1

    def test_bom_item_quantity_positive(self):
        with pytest.raises(ValidationError):
            BOMItemDTO(material_code="X", quantity=0)


class TestProcessRouteDTO:
    def test_with_steps(self):
        route = ProcessRouteDTO(
            product_code="WIDGET-A",
            name="Main Route",
            steps=[
                RouteStepDTO(sequence=1, name="Cut"),
                RouteStepDTO(sequence=2, name="Assemble"),
            ],
        )
        assert len(route.steps) == 2

    def test_step_sequence_nonnegative(self):
        with pytest.raises(ValidationError):
            RouteStepDTO(sequence=0, name="Bad")


class TestWorkCellDTO:
    def test_minimal(self):
        dto = WorkCellDTO(code="WC-01", name="Work Cell 1")
        assert dto.area_code is None


# ═══════════════════════════════════════════════════════════════════
# Outbound DTOs
# ═══════════════════════════════════════════════════════════════════


class TestERPConfirmation:
    def test_success(self):
        conf = ERPConfirmation(success=True, erp_doc_number="DOC-001")
        assert conf.success is True
        assert conf.message == ""

    def test_failure(self):
        conf = ERPConfirmation(success=False, message="timeout")
        assert conf.erp_doc_number is None


class TestCompletionReport:
    def test_valid(self):
        r = CompletionReport(erp_reference="PO-1", qty_good=10, qty_reject=2)
        assert r.uom == "EA"

    def test_qty_nonnegative(self):
        with pytest.raises(ValidationError):
            CompletionReport(erp_reference="PO-1", qty_good=-1)


class TestConsumptionReport:
    def test_with_materials(self):
        r = ConsumptionReport(
            erp_reference="PO-1",
            materials=[MaterialConsumptionDTO(material_code="STEEL", quantity=5.0)],
        )
        assert len(r.materials) == 1

    def test_material_quantity_positive(self):
        with pytest.raises(ValidationError):
            MaterialConsumptionDTO(material_code="X", quantity=0)


class TestScrapReport:
    def test_valid(self):
        r = ScrapReport(erp_reference="PO-1", qty_scrapped=3, reason_code="DEFECT")
        assert r.uom == "EA"


class TestLaborReport:
    def test_valid(self):
        r = LaborReport(
            erp_reference="PO-1", operator_id="OP-1", duration_minutes=30.0,
        )
        assert r.step_id is None


class TestDowntimeReport:
    def test_valid(self):
        now = datetime.now(timezone.utc)
        r = DowntimeReport(
            equipment_id="EQ-1",
            duration_minutes=15.0,
            reason_code="MAINT",
            started_at=now,
        )
        assert r.equipment_id == "EQ-1"


class TestQualityResultReport:
    def test_valid(self):
        r = QualityResultReport(
            erp_reference="PO-1",
            test_id="T-1",
            result="pass",
            details={"measurement": 10.0},
        )
        assert r.details["measurement"] == 10.0


# ═══════════════════════════════════════════════════════════════════
# Mock ERP Inbound Adapter
# ═══════════════════════════════════════════════════════════════════


class TestMockERPTransformLayer:
    def test_passthrough_operations_request(self):
        layer = MockERPTransformLayer()
        data = {"erp_reference": "PO-1", "product_code": "W", "quantity_ordered": 10}
        result = layer.to_operations_request(data)
        assert isinstance(result, OperationsRequestDTO)
        assert result.erp_reference == "PO-1"

    def test_passthrough_material(self):
        layer = MockERPTransformLayer()
        data = {"code": "MAT-1", "name": "Steel"}
        result = layer.to_material(data)
        assert isinstance(result, MaterialDefinitionDTO)


class TestMockERPInboundAdapter:
    @pytest.fixture
    def adapter(self):
        return MockERPInboundAdapter(latency_ms=0, failure_rate=0.0)

    @pytest.mark.asyncio
    async def test_lifecycle(self, adapter):
        assert await adapter.health_check() is False
        await adapter.connect()
        assert await adapter.health_check() is True
        await adapter.disconnect()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_sync_operations_requests(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_operations_requests()
        assert len(orders) == 3
        assert all(isinstance(o, OperationsRequestDTO) for o in orders)
        assert orders[0].erp_reference == "PO-2026-001"

    @pytest.mark.asyncio
    async def test_sync_materials(self, adapter):
        await adapter.connect()
        mats = await adapter.sync_materials()
        assert len(mats) == 4
        assert all(isinstance(m, MaterialDefinitionDTO) for m in mats)

    @pytest.mark.asyncio
    async def test_sync_products(self, adapter):
        await adapter.connect()
        prods = await adapter.sync_products()
        assert len(prods) == 3
        assert all(isinstance(p, ProductDefinitionDTO) for p in prods)

    @pytest.mark.asyncio
    async def test_sync_boms_empty(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("any")
        assert boms == []

    @pytest.mark.asyncio
    async def test_sync_routings_empty(self, adapter):
        await adapter.connect()
        routings = await adapter.sync_routings("any")
        assert routings == []

    @pytest.mark.asyncio
    async def test_sync_work_cells_empty(self, adapter):
        await adapter.connect()
        cells = await adapter.sync_work_cells()
        assert cells == []


# ═══════════════════════════════════════════════════════════════════
# Mock ERP Outbound Adapter
# ═══════════════════════════════════════════════════════════════════


class TestMockERPOutboundAdapter:
    @pytest.fixture
    def adapter(self):
        return MockERPOutboundAdapter(latency_ms=0, failure_rate=0.0)

    @pytest.mark.asyncio
    async def test_lifecycle(self, adapter):
        assert await adapter.health_check() is False
        await adapter.connect()
        assert await adapter.health_check() is True
        await adapter.disconnect()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_report_completion(self, adapter):
        await adapter.connect()
        conf = await adapter.report_completion("PO-1", qty_good=10, qty_reject=2)
        assert isinstance(conf, ERPConfirmation)
        assert conf.success is True
        assert conf.erp_doc_number == "MOCK-0001"
        assert len(adapter.reports) == 1
        assert adapter.reports[0]["type"] == "completion"

    @pytest.mark.asyncio
    async def test_report_consumption(self, adapter):
        await adapter.connect()
        materials = [MaterialConsumptionDTO(material_code="STEEL", quantity=5.0)]
        conf = await adapter.report_consumption("PO-1", materials)
        assert conf.success is True
        assert adapter.reports[0]["type"] == "consumption"

    @pytest.mark.asyncio
    async def test_report_scrap(self, adapter):
        await adapter.connect()
        conf = await adapter.report_scrap("PO-1", qty_scrapped=3, reason_code="DEFECT")
        assert conf.success is True
        assert adapter.reports[0]["type"] == "scrap"

    @pytest.mark.asyncio
    async def test_report_labor(self, adapter):
        await adapter.connect()
        conf = await adapter.report_labor("PO-1", operator_id="OP-1", duration_minutes=30.0)
        assert conf.success is True
        assert adapter.reports[0]["type"] == "labor"

    @pytest.mark.asyncio
    async def test_report_downtime(self, adapter):
        await adapter.connect()
        now = datetime.now(timezone.utc)
        conf = await adapter.report_downtime("EQ-1", duration_minutes=15.0, reason_code="MAINT", started_at=now)
        assert conf.success is True
        assert adapter.reports[0]["type"] == "downtime"

    @pytest.mark.asyncio
    async def test_report_quality_result(self, adapter):
        await adapter.connect()
        conf = await adapter.report_quality_result("PO-1", test_id="T-1", result="pass", details={"v": 1})
        assert conf.success is True
        assert adapter.reports[0]["type"] == "quality_result"

    @pytest.mark.asyncio
    async def test_doc_counter_increments(self, adapter):
        await adapter.connect()
        c1 = await adapter.report_completion("PO-1", qty_good=1, qty_reject=0)
        c2 = await adapter.report_completion("PO-2", qty_good=2, qty_reject=0)
        assert c1.erp_doc_number == "MOCK-0001"
        assert c2.erp_doc_number == "MOCK-0002"

    @pytest.mark.asyncio
    async def test_reports_property_returns_copy(self, adapter):
        await adapter.connect()
        await adapter.report_completion("PO-1", qty_good=1, qty_reject=0)
        reps = adapter.reports
        reps.clear()
        assert len(adapter.reports) == 1  # internal list unchanged


# ═══════════════════════════════════════════════════════════════════
# ERP Outbound Handler Registration Tests
# ═══════════════════════════════════════════════════════════════════


class TestERPOutboundHandlers:
    def test_handlers_module_importable(self):
        import mes.adapters.erp.handlers  # noqa: F401

    def test_event_handlers_registered(self):
        from mes.framework.events.decorators import get_registered_handlers
        handlers = get_registered_handlers()
        event_types = [h[0] for h in handlers]
        # ERP handlers subscribe to completion events
        assert "wip.lot.completed" in event_types
        assert "wip.unit.completed" in event_types

    def test_handler_functions_exist(self):
        import inspect
        from mes.adapters.erp.handlers import (
            on_lot_completed_erp_report,
            on_unit_completed_erp_report,
        )
        assert inspect.iscoroutinefunction(on_lot_completed_erp_report)
        assert inspect.iscoroutinefunction(on_unit_completed_erp_report)


# ═══════════════════════════════════════════════════════════════════
# ProcessRouteDTO → MES Route Mapping Tests
# ═══════════════════════════════════════════════════════════════════


class TestProcessRouteDTOMapping:
    def test_route_dto_with_steps(self):
        dto = ProcessRouteDTO(
            product_code="FG-WIDGET-100",
            name="50000001",
            version="01",
            steps=[
                RouteStepDTO(sequence=10, name="Cut", step_type="production", work_center_code="WC-CUT-01"),
                RouteStepDTO(sequence=20, name="Test", step_type="inspection", work_center_code="WC-TEST-01"),
            ],
        )
        assert dto.product_code == "FG-WIDGET-100"
        assert len(dto.steps) == 2
        assert dto.steps[0].work_center_code == "WC-CUT-01"
        assert dto.steps[1].step_type == "inspection"

    def test_route_step_dto_defaults(self):
        step = RouteStepDTO(sequence=1, name="Step 1")
        assert step.step_type == "production"
        assert step.work_center_code is None
        assert step.description == ""

    def test_route_dto_metadata(self):
        dto = ProcessRouteDTO(
            product_code="P1",
            name="R1",
            metadata={"plant": "1000"},
        )
        assert dto.metadata["plant"] == "1000"

    def test_route_step_sequence_validation(self):
        with pytest.raises(ValidationError):
            RouteStepDTO(sequence=0, name="Bad")


# ═══════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════


class TestERPExceptions:
    def test_connection_error(self):
        exc = ERPConnectionError()
        assert exc.status_code == 502
        assert exc.error_code == "ERP_CONNECTION_ERROR"
        assert "Cannot connect" in str(exc)

    def test_sync_error(self):
        exc = ERPSyncError(message="failed to pull orders")
        assert exc.status_code == 502
        assert "failed to pull orders" in str(exc)

    def test_outbound_error(self):
        exc = ERPOutboundError()
        assert exc.status_code == 502
        assert exc.error_code == "ERP_OUTBOUND_ERROR"


# ═══════════════════════════════════════════════════════════════════
# Queue schemas and events
# ═══════════════════════════════════════════════════════════════════


class TestQueueSchemas:
    def test_queue_statuses(self):
        assert "pending" in QUEUE_STATUSES
        assert "sent" in QUEUE_STATUSES
        assert "failed" in QUEUE_STATUSES
        assert "retry" in QUEUE_STATUSES

    def test_report_types(self):
        assert "completion" in REPORT_TYPES
        assert "consumption" in REPORT_TYPES
        assert "quality_result" in REPORT_TYPES

    def test_queue_item_create(self):
        item = QueueItemCreate(
            report_type="completion",
            payload={"order_id": "PO-1", "qty_good": 10},
        )
        assert item.max_attempts == 5

    def test_queue_item_create_max_attempts_bound(self):
        with pytest.raises(ValidationError):
            QueueItemCreate(report_type="completion", payload={}, max_attempts=0)
        with pytest.raises(ValidationError):
            QueueItemCreate(report_type="completion", payload={}, max_attempts=21)

    def test_queue_stats_defaults(self):
        stats = QueueStats()
        assert stats.pending == 0
        assert stats.total == 0


class TestQueueEvents:
    def test_outbound_sent_event(self):
        event = erp_outbound_sent("completion", "DOC-001")
        assert event.event_type == "erp.outbound.sent"
        assert event.source == "erp_adapter"
        assert event.payload["report_type"] == "completion"
        assert event.payload["erp_doc_number"] == "DOC-001"

    def test_outbound_failed_event(self):
        event = erp_outbound_failed("Q-1", "scrap", "timeout", 5)
        assert event.event_type == "erp.outbound.failed"
        assert event.payload["queue_item_id"] == "Q-1"
        assert event.payload["attempts"] == 5
