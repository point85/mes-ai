"""
Unit tests for the Oracle Cloud ERP Simulator plugin.

Covers:
- OracleSimulatorInboundAdapter (all sync methods, transform pipeline)
- OracleSimulatorOutboundAdapter (all report methods, transaction numbers)
- OracleERPSimulatorPlugin (lifecycle, health, get_adapter)
- Oracle data integrity (field names, BOM structures, routing operations)
- Build-material helpers for vendor-agnostic CRUD
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mes.adapters.erp.dtos import (
    BillOfMaterialDTO,
    ERPConfirmation,
    MaterialConsumptionDTO,
    MaterialDefinitionDTO,
    ProcessRouteDTO,
    ProductDefinitionDTO,
    OperationsRequestDTO,
    WorkCellDTO,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_inbound(**overrides):
    from plugins.system.oracle_erp_simulator.simulator import OracleSimulatorInboundAdapter
    defaults = {"organization_code": "ORG_MAIN", "business_unit": "BU_MANUFACTURING", "latency_ms": 0, "failure_rate": 0.0}
    defaults.update(overrides)
    return OracleSimulatorInboundAdapter(**defaults)


def _make_outbound(**overrides):
    from plugins.system.oracle_erp_simulator.simulator import OracleSimulatorOutboundAdapter
    defaults = {"organization_code": "ORG_MAIN", "business_unit": "BU_MANUFACTURING", "latency_ms": 0, "failure_rate": 0.0}
    defaults.update(overrides)
    return OracleSimulatorOutboundAdapter(**defaults)


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Work Orders (Production Orders)
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorWorkOrders:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_sync_all_orders(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_operations_requests()
        assert len(orders) == 5
        assert all(isinstance(o, OperationsRequestDTO) for o in orders)

    @pytest.mark.asyncio
    async def test_order_field_mapping(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_operations_requests()
        o = orders[0]
        assert o.erp_reference == "WO-100-001"
        assert o.product_code == "FG-WIDGET-100"
        assert o.quantity_ordered == 100
        assert o.uom == "EA"
        assert o.bom_id == "PRIMARY"
        assert o.routing_id == "RTG-WIDGET-100"
        assert o.metadata["oracle_org_code"] == "ORG_MAIN"
        assert o.metadata["oracle_work_order_type"] == "Standard"

    @pytest.mark.asyncio
    async def test_oracle_priority_mapping(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_operations_requests()
        assert orders[0].priority == 500   # "3" → Medium
        assert orders[1].priority == 700   # "2" → High
        assert orders[2].priority == 900   # "1" → Critical
        assert orders[4].priority == 300   # "4" → Low

    @pytest.mark.asyncio
    async def test_planned_dates_parsed(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_operations_requests()
        o = orders[0]
        assert o.planned_start is not None
        assert isinstance(o.planned_start, datetime)
        assert o.planned_start.year == 2026

    @pytest.mark.asyncio
    async def test_incremental_sync(self, adapter):
        await adapter.connect()
        cutoff = datetime(2026, 3, 25, tzinfo=timezone.utc)
        orders = await adapter.sync_operations_requests(since=cutoff)
        assert len(orders) == 1
        assert orders[0].erp_reference == "WO-300-002"

    @pytest.mark.asyncio
    async def test_add_work_order(self, adapter):
        await adapter.connect()
        adapter.add_operations_request({
            "WorkOrderNumber": "WO-TEST-999",
            "ItemNumber": "FG-WIDGET-100",
            "PlannedQuantity": 10,
            "WorkOrderPriority": "1",
            "UOMCode": "EA",
            "OrganizationCode": "ORG_MAIN",
            "WorkOrderType": "Standard",
        })
        orders = await adapter.sync_operations_requests()
        assert len(orders) == 6
        added = [o for o in orders if o.erp_reference == "WO-TEST-999"]
        assert len(added) == 1
        assert added[0].quantity_ordered == 10


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Materials
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorMaterials:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_sync_all_materials(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        assert len(materials) == 20
        assert all(isinstance(m, MaterialDefinitionDTO) for m in materials)

    @pytest.mark.asyncio
    async def test_raw_material_mapping(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        steel = next(m for m in materials if m.code == "RM-STEEL-1MM")
        assert steel.name == "Carbon Steel Sheet 1 mm"
        assert steel.material_type == "raw"
        assert steel.uom == "kg"

    @pytest.mark.asyncio
    async def test_subassembly_mapping(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        pcb = next(m for m in materials if m.code == "SF-PCB-CTRL")
        assert pcb.material_type == "semi"

    @pytest.mark.asyncio
    async def test_finished_good_mapping(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        widget = next(m for m in materials if m.code == "FG-WIDGET-100")
        assert widget.material_type == "finished"
        assert widget.revision == "A"

    @pytest.mark.asyncio
    async def test_shelf_life(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        pellets = next(m for m in materials if m.code == "RM-ABS-PELLET")
        assert pellets.shelf_life_days == 730

    @pytest.mark.asyncio
    async def test_oracle_metadata_preserved(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        steel = next(m for m in materials if m.code == "RM-STEEL-1MM")
        assert steel.metadata["oracle_item_class"] == "Raw Material"
        assert steel.metadata["oracle_item_type"] == "STANDARD"
        assert steel.metadata["oracle_org_code"] == "ORG_MAIN"


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Products
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorProducts:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_sync_all_products(self, adapter):
        await adapter.connect()
        products = await adapter.sync_products()
        assert len(products) == 3
        assert all(isinstance(p, ProductDefinitionDTO) for p in products)

    @pytest.mark.asyncio
    async def test_product_field_mapping(self, adapter):
        await adapter.connect()
        products = await adapter.sync_products()
        w100 = next(p for p in products if p.code == "FG-WIDGET-100")
        assert w100.name == "Standard Widget 100"
        assert w100.product_type == "discrete"
        assert w100.version == "A"


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Bills of Material
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorBOMs:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_bom_for_widget_100(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("FG-WIDGET-100")
        assert len(boms) == 1
        bom = boms[0]
        assert isinstance(bom, BillOfMaterialDTO)
        assert bom.product_code == "FG-WIDGET-100"
        assert bom.version == "1"
        assert len(bom.items) == 4

    @pytest.mark.asyncio
    async def test_bom_items_widget_100(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("FG-WIDGET-100")
        items = boms[0].items
        codes = [i.material_code for i in items]
        assert "SF-HOUSING-STEEL" in codes
        assert "SF-PCB-CTRL" in codes
        assert "RM-SCREW-M3" in codes
        assert "RM-LABEL-PROD" in codes

    @pytest.mark.asyncio
    async def test_bom_item_quantities(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("FG-WIDGET-100")
        items = {i.material_code: i for i in boms[0].items}
        assert items["SF-HOUSING-STEEL"].quantity == 1.0
        assert items["RM-SCREW-M3"].quantity == 6.0
        assert items["RM-SCREW-M3"].uom == "EA"

    @pytest.mark.asyncio
    async def test_bom_for_gadget_300(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("FG-GADGET-300")
        assert len(boms) == 1
        items = boms[0].items
        assert len(items) == 6
        codes = [i.material_code for i in items]
        assert "RM-BATTERY-LIPO" in codes
        assert "RM-SENSOR-TEMP" in codes

    @pytest.mark.asyncio
    async def test_bom_unknown_product(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("NONEXISTENT")
        assert boms == []

    @pytest.mark.asyncio
    async def test_bom_metadata(self, adapter):
        await adapter.connect()
        boms = await adapter.sync_boms("FG-WIDGET-200")
        bom = boms[0]
        assert bom.metadata["oracle_structure_name"] == "PRIMARY"
        assert bom.metadata["oracle_org_code"] == "ORG_MAIN"

    @pytest.mark.asyncio
    async def test_add_bom(self, adapter):
        await adapter.connect()
        adapter.add_bom("FG-WIDGET-100", {
            "ItemNumber": "FG-WIDGET-100",
            "StructureName": "ALTERNATE",
            "AlternateDesignator": "2",
            "OrganizationCode": "ORG_MAIN",
            "Component": [
                {
                    "ComponentItemNumber": "RM-STEEL-1MM",
                    "ComponentQuantity": "5",
                    "UOMCode": "KG",
                    "ComponentSequenceNumber": "10",
                },
            ],
        })
        boms = await adapter.sync_boms("FG-WIDGET-100")
        assert len(boms) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Routings
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorRoutings:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_routing_for_widget_100(self, adapter):
        await adapter.connect()
        routes = await adapter.sync_routings("FG-WIDGET-100")
        assert len(routes) == 1
        route = routes[0]
        assert isinstance(route, ProcessRouteDTO)
        assert route.product_code == "FG-WIDGET-100"
        assert route.name == "RTG-WIDGET-100"

    @pytest.mark.asyncio
    async def test_routing_operations_sorted(self, adapter):
        await adapter.connect()
        routes = await adapter.sync_routings("FG-WIDGET-100")
        steps = routes[0].steps
        assert len(steps) == 5
        sequences = [s.sequence for s in steps]
        assert sequences == sorted(sequences)

    @pytest.mark.asyncio
    async def test_routing_step_types(self, adapter):
        await adapter.connect()
        routes = await adapter.sync_routings("FG-WIDGET-100")
        steps = routes[0].steps
        test_step = next(s for s in steps if s.name == "Functional test")
        assert test_step.step_type == "inspection"
        cut_step = next(s for s in steps if "Cut" in s.name)
        assert cut_step.step_type == "production"

    @pytest.mark.asyncio
    async def test_routing_work_centers(self, adapter):
        await adapter.connect()
        routes = await adapter.sync_routings("FG-WIDGET-200")
        steps = routes[0].steps
        wc_codes = [s.work_center_code for s in steps]
        assert "WC-CNC-01" in wc_codes
        assert "WC-FINISH-01" in wc_codes
        assert "WC-TEST-01" in wc_codes

    @pytest.mark.asyncio
    async def test_gadget_routing_operations(self, adapter):
        await adapter.connect()
        routes = await adapter.sync_routings("FG-GADGET-300")
        steps = routes[0].steps
        assert len(steps) == 6
        names = [s.name for s in steps]
        assert "Injection mould ABS case" in names
        assert "Burn-in and functional test" in names

    @pytest.mark.asyncio
    async def test_routing_unknown_product(self, adapter):
        await adapter.connect()
        routes = await adapter.sync_routings("NONEXISTENT")
        assert routes == []


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Work Centers
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorWorkCenters:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_sync_all_work_centers(self, adapter):
        await adapter.connect()
        wcs = await adapter.sync_work_cells()
        assert len(wcs) == 10
        assert all(isinstance(wc, WorkCellDTO) for wc in wcs)

    @pytest.mark.asyncio
    async def test_work_center_field_mapping(self, adapter):
        await adapter.connect()
        wcs = await adapter.sync_work_cells()
        smt = next(wc for wc in wcs if wc.code == "WC-SMT-01")
        assert smt.name == "SMT Pick-and-Place Line 01"
        assert smt.area_code == "ORG_MAIN"
        assert smt.capabilities["oracle_work_center_type"] == "Line"


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Lifecycle & Error Simulation
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorInboundLifecycle:

    @pytest.mark.asyncio
    async def test_health_disconnected(self):
        adapter = _make_inbound()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_health_connected(self):
        adapter = _make_inbound()
        await adapter.connect()
        assert await adapter.health_check() is True
        await adapter.disconnect()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_failure_simulation(self):
        adapter = _make_inbound(failure_rate=1.0)
        await adapter.connect()
        from mes.adapters.erp.exceptions import ERPSyncError
        with pytest.raises(ERPSyncError):
            await adapter.sync_operations_requests()

    @pytest.mark.asyncio
    async def test_independent_instances(self):
        a1 = _make_inbound()
        a2 = _make_inbound()
        await a1.connect()
        await a2.connect()
        a1.add_operations_request({
            "WorkOrderNumber": "WO-TEST-999",
            "ItemNumber": "X",
            "PlannedQuantity": 1,
            "UOMCode": "EA",
            "OrganizationCode": "ORG_MAIN",
            "WorkOrderType": "Standard",
        })
        assert len(await a1.sync_operations_requests()) == 6
        assert len(await a2.sync_operations_requests()) == 5

    @pytest.mark.asyncio
    async def test_erp_type_attribute(self):
        adapter = _make_inbound()
        assert adapter.erp_type == "oracle"


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Completion Transactions
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorCompletions:

    @pytest.fixture
    def adapter(self):
        return _make_outbound()

    @pytest.mark.asyncio
    async def test_report_completion(self, adapter):
        await adapter.connect()
        result = await adapter.report_completion(
            order_id="WO-100-001",
            qty_good=95,
            qty_reject=5,
            step_id="10",
        )
        assert isinstance(result, ERPConfirmation)
        assert result.success is True
        assert result.erp_doc_number is not None

    @pytest.mark.asyncio
    async def test_completion_oracle_payload(self, adapter):
        await adapter.connect()
        await adapter.report_completion(
            order_id="WO-100-001",
            qty_good=95,
            qty_reject=5,
            step_id="10",
        )
        assert len(adapter.confirmations) == 1
        record = adapter.confirmations[0]
        assert record["type"] == "wip_completion"
        payload = record["erp_payload"]
        assert payload["WorkOrderNumber"] == "WO-100-001"
        assert payload["CompletedQuantity"] == 95
        assert payload["RejectedQuantity"] == 5
        assert payload["TransactionType"] == "WIP_COMPLETION"

    @pytest.mark.asyncio
    async def test_sequential_txn_numbers(self, adapter):
        await adapter.connect()
        r1 = await adapter.report_completion("WO-100-001", 10, 0)
        r2 = await adapter.report_completion("WO-100-001", 20, 0)
        n1 = int(r1.erp_doc_number)
        n2 = int(r2.erp_doc_number)
        assert n2 == n1 + 1


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Consumption / Material Issue
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorConsumption:

    @pytest.fixture
    def adapter(self):
        return _make_outbound()

    @pytest.mark.asyncio
    async def test_report_consumption(self, adapter):
        await adapter.connect()
        result = await adapter.report_consumption(
            order_id="WO-100-001",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-STEEL-1MM",
                    quantity=2.5,
                    uom="KG",
                    lot_number="LOT-STEEL-001",
                ),
                MaterialConsumptionDTO(
                    material_code="RM-SCREW-M3",
                    quantity=600.0,
                    uom="EA",
                ),
            ],
        )
        assert result.success is True
        assert "WIP_ISSUE" in result.message

    @pytest.mark.asyncio
    async def test_consumption_oracle_payload(self, adapter):
        await adapter.connect()
        await adapter.report_consumption(
            order_id="WO-100-001",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-STEEL-1MM",
                    quantity=2.5,
                    uom="KG",
                    lot_number="LOT-001",
                ),
            ],
        )
        record = adapter.confirmations[0]
        assert record["type"] == "wip_material_issue"
        payload = record["erp_payload"]
        assert payload["WorkOrderNumber"] == "WO-100-001"
        txns = payload["MaterialTransactions"]
        assert len(txns) == 1
        assert txns[0]["ItemNumber"] == "RM-STEEL-1MM"
        assert txns[0]["TransactionType"] == "WIP_ISSUE"


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Scrap, Labor, Downtime, Quality
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorOtherReports:

    @pytest.fixture
    def adapter(self):
        return _make_outbound()

    @pytest.mark.asyncio
    async def test_report_scrap(self, adapter):
        await adapter.connect()
        result = await adapter.report_scrap(
            order_id="WO-100-001",
            qty_scrapped=3,
            reason_code="DEFECTIVE_PCB",
        )
        assert result.success is True
        record = adapter.confirmations[0]
        assert record["erp_payload"]["TransactionType"] == "WIP_SCRAP"
        assert record["erp_payload"]["ReasonCode"] == "DEFECTIVE_PCB"

    @pytest.mark.asyncio
    async def test_report_labor(self, adapter):
        await adapter.connect()
        result = await adapter.report_labor(
            order_id="WO-100-001",
            operator_id="EMP-1234",
            duration_minutes=45.5,
        )
        assert result.success is True
        record = adapter.confirmations[0]
        assert record["type"] == "resource_transaction"
        assert record["erp_payload"]["ResourceCode"] == "EMP-1234"
        assert record["erp_payload"]["UOMCode"] == "MIN"

    @pytest.mark.asyncio
    async def test_report_downtime(self, adapter):
        await adapter.connect()
        started = datetime(2026, 3, 22, 14, 30, 0, tzinfo=timezone.utc)
        result = await adapter.report_downtime(
            equipment_id="WC-SMT-01",
            duration_minutes=120.0,
            reason_code="CONVEYOR_JAM",
            started_at=started,
        )
        assert result.success is True
        record = adapter.confirmations[0]
        assert record["type"] == "maintenance_event"
        assert record["erp_payload"]["AssetNumber"] == "WC-SMT-01"
        assert record["erp_payload"]["TransactionType"] == "MAINTENANCE_EVENT"

    @pytest.mark.asyncio
    async def test_report_quality_result(self, adapter):
        await adapter.connect()
        result = await adapter.report_quality_result(
            order_id="WO-200-001",
            test_id="FUNC-TEST-001",
            result="PASS",
            details={"voltage": 3.31, "current_ma": 250},
        )
        assert result.success is True
        record = adapter.confirmations[0]
        assert record["type"] == "quality_result"
        assert record["erp_payload"]["InspectionPlanCode"] == "FUNC-TEST-001"


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Lifecycle & Error Simulation
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorOutboundLifecycle:

    @pytest.mark.asyncio
    async def test_health_disconnected(self):
        adapter = _make_outbound()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_health_connected(self):
        adapter = _make_outbound()
        await adapter.connect()
        assert await adapter.health_check() is True
        await adapter.disconnect()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_failure_simulation(self):
        adapter = _make_outbound(failure_rate=1.0)
        await adapter.connect()
        from mes.adapters.erp.exceptions import ERPOutboundError
        with pytest.raises(ERPOutboundError):
            await adapter.report_completion("WO-1", 10, 0)


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Wrapper
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleERPSimulatorPlugin:

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        from plugins.system.oracle_erp_simulator.plugin import OracleERPSimulatorPlugin
        plugin = OracleERPSimulatorPlugin()
        await plugin.initialize({"organization_code": "ORG_MAIN", "business_unit": "BU_MANUFACTURING"})
        await plugin.start()
        assert await plugin.health_check() is True

        adapters = plugin.get_adapter()
        assert "erp_inbound" in adapters
        assert "erp_outbound" in adapters
        assert adapters["erp_inbound"] is not None
        assert adapters["erp_outbound"] is not None


# ═══════════════════════════════════════════════════════════════════════════
# Simulator Material CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleSimulatorMaterialCRUD:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    def test_get_material_found(self, adapter):
        mat = adapter.get_material("RM-STEEL-1MM")
        assert mat is not None
        assert mat["ItemNumber"] == "RM-STEEL-1MM"

    def test_get_material_not_found(self, adapter):
        assert adapter.get_material("NONEXISTENT") is None

    def test_add_and_get_material(self, adapter):
        oracle_rec = {
            "ItemNumber": "TEST-MAT-001",
            "Description": "Test Material",
            "ItemType": "STANDARD",
            "PrimaryUOMCode": "KG",
            "LongDescription": "A test material",
            "ShelfLifeDays": None,
            "ItemClass": "Raw Material",
            "OrganizationCode": "ORG_MAIN",
        }
        adapter.add_material(oracle_rec)
        found = adapter.get_material("TEST-MAT-001")
        assert found is not None
        assert found["Description"] == "Test Material"

    def test_update_material_existing(self, adapter):
        result = adapter.update_material("RM-STEEL-1MM", {"Description": "Updated Name"})
        assert result is not None
        assert result["Description"] == "Updated Name"
        assert adapter.get_material("RM-STEEL-1MM")["Description"] == "Updated Name"

    def test_update_material_not_found(self, adapter):
        assert adapter.update_material("NONEXISTENT", {"Description": "X"}) is None

    def test_delete_material_existing(self, adapter):
        initial_count = len(adapter._materials)
        assert adapter.delete_material("RM-STEEL-1MM") is True
        assert len(adapter._materials) == initial_count - 1
        assert adapter.get_material("RM-STEEL-1MM") is None

    def test_delete_material_not_found(self, adapter):
        initial_count = len(adapter._materials)
        assert adapter.delete_material("NONEXISTENT") is False
        assert len(adapter._materials) == initial_count

    @pytest.mark.asyncio
    async def test_create_then_sync_returns_new_material(self, adapter):
        await adapter.connect()
        initial = await adapter.sync_materials()
        initial_count = len(initial)

        adapter.add_material({
            "ItemNumber": "NEW-MAT-999",
            "Description": "New Material",
            "ItemType": "FINISHED_GOOD",
            "PrimaryUOMCode": "EA",
            "LongDescription": "Brand new",
            "ShelfLifeDays": 365,
            "ItemClass": "Finished Good",
            "OrganizationCode": "ORG_MAIN",
        })

        updated = await adapter.sync_materials()
        assert len(updated) == initial_count + 1
        new = [m for m in updated if m.code == "NEW-MAT-999"]
        assert len(new) == 1
        assert new[0].name == "New Material"
        assert new[0].shelf_life_days == 365


# ═══════════════════════════════════════════════════════════════════════════
# Build-material helpers for vendor-agnostic CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestOracleBuildMaterialHelpers:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    def test_build_material_record(self, adapter):
        rec = adapter.build_material_record(
            code="TEST-001", name="Test Item", material_type="STANDARD",
            uom="KG", revision="A", description="Test desc", shelf_life_days=90,
        )
        assert rec["ItemNumber"] == "TEST-001"
        assert rec["Description"] == "Test Item"
        assert rec["ItemType"] == "STANDARD"
        assert rec["PrimaryUOMCode"] == "KG"
        assert rec["RevisionCode"] == "A"
        assert rec["LongDescription"] == "Test desc"
        assert rec["ShelfLifeDays"] == 90
        assert rec["OrganizationCode"] == "ORG_MAIN"

    def test_build_material_updates(self, adapter):
        updates = adapter.build_material_updates(
            name="Updated", uom="EA",
        )
        assert updates == {"Description": "Updated", "PrimaryUOMCode": "EA"}

    def test_build_material_updates_empty(self, adapter):
        updates = adapter.build_material_updates()
        assert updates == {}

    def test_material_type_options(self, adapter):
        opts = adapter.material_type_options()
        assert len(opts) >= 3
        codes = [o["code"] for o in opts]
        assert "STANDARD" in codes
        assert "FINISHED_GOOD" in codes
        assert "SUBASSEMBLY" in codes


class TestSAPBuildMaterialHelpers:
    """Verify the SAP adapter also has the same build helpers."""

    @pytest.fixture
    def adapter(self):
        return _make_sap_inbound()

    def test_build_material_record(self, adapter):
        rec = adapter.build_material_record(
            code="TEST-001", name="Test Material", material_type="ROH",
            uom="KG", revision="A", description="Test", shelf_life_days=90,
        )
        assert rec["Material"] == "TEST-001"
        assert rec["MaterialName"] == "Test Material"
        assert rec["MaterialType"] == "ROH"
        assert rec["BaseUnit"] == "KG"
        assert rec["MaterialRevisionLevel"] == "A"
        assert rec["MaximumStoragePeriod"] == "90"

    def test_build_material_updates(self, adapter):
        updates = adapter.build_material_updates(name="Updated", uom="EA")
        assert updates == {"MaterialName": "Updated", "BaseUnit": "EA"}

    def test_material_type_options(self, adapter):
        opts = adapter.material_type_options()
        codes = [o["code"] for o in opts]
        assert "ROH" in codes
        assert "FERT" in codes

    def test_erp_type(self, adapter):
        assert adapter.erp_type == "sap"


def _make_sap_inbound(**overrides):
    from plugins.system.sap_erp_simulator.simulator import SAPSimulatorInboundAdapter
    defaults = {"plant": "1000", "company_code": "1000", "latency_ms": 0, "failure_rate": 0.0}
    defaults.update(overrides)
    return SAPSimulatorInboundAdapter(**defaults)
