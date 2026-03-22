"""
Unit tests for the SAP ERP Simulator plugin.

Covers:
- SAPSimulatorInboundAdapter (all sync methods, transform pipeline, incremental sync)
- SAPSimulatorOutboundAdapter (all report methods, SAP doc numbers, payload validation)
- SAPERPSimulatorPlugin (lifecycle, health, get_adapter)
- SAP data integrity (field names, BOM structures, routing operations)
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
    ProductionOrderDTO,
    WorkCellDTO,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_inbound(**overrides):
    from plugins.system.sap_erp_simulator.simulator import SAPSimulatorInboundAdapter
    defaults = {"plant": "1000", "company_code": "1000", "latency_ms": 0, "failure_rate": 0.0}
    defaults.update(overrides)
    return SAPSimulatorInboundAdapter(**defaults)


def _make_outbound(**overrides):
    from plugins.system.sap_erp_simulator.simulator import SAPSimulatorOutboundAdapter
    defaults = {"plant": "1000", "company_code": "1000", "latency_ms": 0, "failure_rate": 0.0}
    defaults.update(overrides)
    return SAPSimulatorOutboundAdapter(**defaults)


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Production Orders
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorProductionOrders:

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_sync_all_orders(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_production_orders()
        assert len(orders) == 5
        assert all(isinstance(o, ProductionOrderDTO) for o in orders)

    @pytest.mark.asyncio
    async def test_order_field_mapping(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_production_orders()
        o = orders[0]
        assert o.erp_reference == "000001000100"
        assert o.product_code == "FG-WIDGET-100"
        assert o.quantity_ordered == 100
        assert o.uom == "EA"
        assert o.bom_id == "00001001"
        assert o.routing_id == "50000001"
        assert o.metadata["sap_plant"] == "1000"
        assert o.metadata["sap_order_type"] == "PP01"

    @pytest.mark.asyncio
    async def test_sap_priority_mapping(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_production_orders()
        assert orders[0].priority == 500   # "3" → Medium
        assert orders[1].priority == 700   # "2" → High
        assert orders[2].priority == 900   # "1" → Very high
        assert orders[4].priority == 300   # "4" → Low

    @pytest.mark.asyncio
    async def test_planned_dates_parsed(self, adapter):
        await adapter.connect()
        orders = await adapter.sync_production_orders()
        o = orders[0]
        assert o.planned_start is not None
        assert isinstance(o.planned_start, datetime)
        assert o.planned_start.year == 2026
        assert o.planned_start.month == 3

    @pytest.mark.asyncio
    async def test_incremental_sync(self, adapter):
        await adapter.connect()
        cutoff = datetime(2026, 3, 25, tzinfo=timezone.utc)
        orders = await adapter.sync_production_orders(since=cutoff)
        assert len(orders) == 1
        assert orders[0].erp_reference == "000001000301"

    @pytest.mark.asyncio
    async def test_add_production_order(self, adapter):
        await adapter.connect()
        adapter.add_production_order({
            "ManufacturingOrder": "000009999999",
            "Material": "FG-WIDGET-100",
            "TotalQuantity": "10",
            "MfgOrderPriority": "1",
            "ProductionUnit": "EA",
            "ProductionPlant": "1000",
            "ManufacturingOrderType": "PP01",
        })
        orders = await adapter.sync_production_orders()
        assert len(orders) == 6
        added = [o for o in orders if o.erp_reference == "000009999999"]
        assert len(added) == 1
        assert added[0].quantity_ordered == 10


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Materials
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorMaterials:

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
        assert steel.uom == "KG"

    @pytest.mark.asyncio
    async def test_semi_finished_mapping(self, adapter):
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

    @pytest.mark.asyncio
    async def test_packaging_mapping(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        label = next(m for m in materials if m.code == "RM-LABEL-PROD")
        assert label.material_type == "packaging"

    @pytest.mark.asyncio
    async def test_shelf_life(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        pellets = next(m for m in materials if m.code == "RM-ABS-PELLET")
        assert pellets.shelf_life_days == 730

    @pytest.mark.asyncio
    async def test_sap_metadata_preserved(self, adapter):
        await adapter.connect()
        materials = await adapter.sync_materials()
        steel = next(m for m in materials if m.code == "RM-STEEL-1MM")
        assert steel.metadata["sap_material_group"] == "001"
        assert steel.metadata["sap_material_type"] == "ROH"
        assert steel.metadata["sap_plant"] == "1000"


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Products
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorProducts:

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
        assert w100.version == "1.0"


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Bills of Material
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorBOMs:

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
        assert bom.version == "01"
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
        assert bom.metadata["sap_bom_number"] == "00001002"

    @pytest.mark.asyncio
    async def test_add_bom(self, adapter):
        await adapter.connect()
        adapter.add_bom("FG-WIDGET-100", {
            "Material": "FG-WIDGET-100",
            "BillOfMaterial": "00001099",
            "BillOfMaterialVariant": "02",
            "to_BOMItem": [
                {
                    "BillOfMaterialItemNumber": "0010",
                    "BillOfMaterialComponent": "RM-STEEL-1MM",
                    "BillOfMaterialItemQuantity": "5",
                    "BillOfMaterialItemUnit": "KG",
                },
            ],
        })
        boms = await adapter.sync_boms("FG-WIDGET-100")
        assert len(boms) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Routings
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorRoutings:

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
        assert route.name == "50000001"

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


class TestSAPSimulatorWorkCenters:

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
        assert smt.area_code == "1000"
        assert smt.capabilities["sap_category"] == "0003"


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Adapter — Lifecycle & Error Simulation
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorInboundLifecycle:

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
            await adapter.sync_production_orders()

    @pytest.mark.asyncio
    async def test_independent_instances(self):
        a1 = _make_inbound()
        a2 = _make_inbound()
        await a1.connect()
        await a2.connect()
        a1.add_production_order({
            "ManufacturingOrder": "000099999999",
            "Material": "X",
            "TotalQuantity": "1",
            "ProductionUnit": "EA",
            "ProductionPlant": "1000",
            "ManufacturingOrderType": "PP01",
        })
        assert len(await a1.sync_production_orders()) == 6
        assert len(await a2.sync_production_orders()) == 5


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Completion Confirmations
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorCompletions:

    @pytest.fixture
    def adapter(self):
        return _make_outbound()

    @pytest.mark.asyncio
    async def test_report_completion(self, adapter):
        await adapter.connect()
        result = await adapter.report_completion(
            order_id="000001000100",
            qty_good=95,
            qty_reject=5,
            step_id="0010",
        )
        assert isinstance(result, ERPConfirmation)
        assert result.success is True
        assert result.erp_doc_number is not None
        assert result.erp_doc_number.startswith("49")
        assert len(result.erp_doc_number) == 10

    @pytest.mark.asyncio
    async def test_completion_sap_payload(self, adapter):
        await adapter.connect()
        await adapter.report_completion(
            order_id="000001000100",
            qty_good=95,
            qty_reject=5,
            step_id="0010",
        )
        assert len(adapter.confirmations) == 1
        record = adapter.confirmations[0]
        assert record["type"] == "confirmation"
        payload = record["sap_payload"]
        assert payload["OrderID"] == "000001000100"
        assert payload["ConfirmationYieldQuantity"] == "95"
        assert payload["ConfirmationScrapQuantity"] == "5"
        assert payload["OrderOperation"] == "0010"
        assert payload["ConfirmationUnit"] == "EA"
        assert "PostingDate" in payload

    @pytest.mark.asyncio
    async def test_sequential_doc_numbers(self, adapter):
        await adapter.connect()
        r1 = await adapter.report_completion("000001000100", 10, 0)
        r2 = await adapter.report_completion("000001000100", 20, 0)
        n1 = int(r1.erp_doc_number)
        n2 = int(r2.erp_doc_number)
        assert n2 == n1 + 1


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Consumption / Goods Movements
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorConsumption:

    @pytest.fixture
    def adapter(self):
        return _make_outbound()

    @pytest.mark.asyncio
    async def test_report_consumption(self, adapter):
        await adapter.connect()
        result = await adapter.report_consumption(
            order_id="000001000100",
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
        assert "261" in result.message

    @pytest.mark.asyncio
    async def test_consumption_sap_payload(self, adapter):
        await adapter.connect()
        await adapter.report_consumption(
            order_id="000001000100",
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
        assert record["type"] == "goods_movement_261"
        payload = record["sap_payload"]
        assert payload["OrderID"] == "000001000100"
        items = payload["GoodsMovementItems"]
        assert len(items) == 1
        assert items[0]["Material"] == "RM-STEEL-1MM"
        assert items[0]["GoodsMovementType"] == "261"
        assert items[0]["Batch"] == "LOT-001"


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Scrap, Labor, Downtime, Quality
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorOtherReports:

    @pytest.fixture
    def adapter(self):
        return _make_outbound()

    @pytest.mark.asyncio
    async def test_report_scrap(self, adapter):
        await adapter.connect()
        result = await adapter.report_scrap(
            order_id="000001000100",
            qty_scrapped=3,
            reason_code="DEFECTIVE_PCB",
        )
        assert result.success is True
        assert "531" in result.message
        record = adapter.confirmations[0]
        assert record["sap_payload"]["GoodsMovementType"] == "531"
        assert record["sap_payload"]["ScrapReasonCode"] == "DEFECTIVE_PCB"

    @pytest.mark.asyncio
    async def test_report_labor(self, adapter):
        await adapter.connect()
        result = await adapter.report_labor(
            order_id="000001000100",
            operator_id="EMP-1234",
            duration_minutes=45.5,
        )
        assert result.success is True
        record = adapter.confirmations[0]
        assert record["type"] == "time_confirmation"
        assert record["sap_payload"]["PersonnelNumber"] == "EMP-1234"
        assert record["sap_payload"]["ActivityUnit"] == "MIN"

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
        assert record["type"] == "pm_notification"
        assert record["sap_payload"]["NotificationType"] == "M2"
        assert record["sap_payload"]["TechnicalObject"] == "WC-SMT-01"

    @pytest.mark.asyncio
    async def test_report_quality_result(self, adapter):
        await adapter.connect()
        result = await adapter.report_quality_result(
            order_id="000001000200",
            test_id="FUNC-TEST-001",
            result="PASS",
            details={"voltage": 3.31, "current_ma": 250},
        )
        assert result.success is True
        assert result.erp_doc_number.startswith("200")
        record = adapter.confirmations[0]
        assert record["type"] == "qm_results_recording"
        assert record["sap_payload"]["InspectionCharacteristic"] == "FUNC-TEST-001"


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Adapter — Lifecycle & Error Simulation
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPSimulatorOutboundLifecycle:

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
            await adapter.report_completion("ORDER-1", 10, 0)


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Wrapper
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPERPSimulatorPlugin:

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        from plugins.system.sap_erp_simulator.plugin import SAPERPSimulatorPlugin
        plugin = SAPERPSimulatorPlugin()
        await plugin.initialize({"plant": "1000", "company_code": "1000"})
        await plugin.start()
        assert await plugin.health_check() is True

        adapters = plugin.get_adapter()
        assert "erp_inbound" in adapters
        assert "erp_outbound" in adapters
        assert adapters["erp_inbound"] is not None
        assert adapters["erp_outbound"] is not None

        await plugin.stop()
        assert await plugin.health_check() is False

    @pytest.mark.asyncio
    async def test_inbound_via_plugin(self):
        from plugins.system.sap_erp_simulator.plugin import SAPERPSimulatorPlugin
        plugin = SAPERPSimulatorPlugin()
        await plugin.initialize({})
        await plugin.start()

        inbound = plugin.get_adapter()["erp_inbound"]
        orders = await inbound.sync_production_orders()
        assert len(orders) == 5

        materials = await inbound.sync_materials()
        assert len(materials) > 0

        boms = await inbound.sync_boms("FG-WIDGET-100")
        assert len(boms) == 1
        assert len(boms[0].items) == 4

        await plugin.stop()

    @pytest.mark.asyncio
    async def test_outbound_via_plugin(self):
        from plugins.system.sap_erp_simulator.plugin import SAPERPSimulatorPlugin
        plugin = SAPERPSimulatorPlugin()
        await plugin.initialize({})
        await plugin.start()

        outbound = plugin.get_adapter()["erp_outbound"]
        result = await outbound.report_completion("000001000100", 50, 2, "0010")
        assert result.success is True
        assert result.erp_doc_number.startswith("49")

        await plugin.stop()

    @pytest.mark.asyncio
    async def test_config_passthrough(self):
        from plugins.system.sap_erp_simulator.plugin import SAPERPSimulatorPlugin
        plugin = SAPERPSimulatorPlugin()
        await plugin.initialize({
            "plant": "2000",
            "company_code": "2000",
            "latency_ms": 0,
            "failure_rate": 0.0,
        })
        await plugin.start()

        inbound = plugin.get_adapter()["erp_inbound"]
        assert inbound._plant == "2000"
        assert inbound._company_code == "2000"

        await plugin.stop()


# ═══════════════════════════════════════════════════════════════════════════
# SAP Data Integrity
# ═══════════════════════════════════════════════════════════════════════════


class TestSAPDataIntegrity:
    """Cross-check that SAP fixture data is internally consistent."""

    @pytest.fixture
    def adapter(self):
        return _make_inbound()

    @pytest.mark.asyncio
    async def test_all_bom_materials_exist(self, adapter):
        """Every BOM component should appear in the material master."""
        await adapter.connect()
        materials = await adapter.sync_materials()
        mat_codes = {m.code for m in materials}

        for product_id in ["FG-WIDGET-100", "FG-WIDGET-200", "FG-GADGET-300"]:
            boms = await adapter.sync_boms(product_id)
            for bom in boms:
                for item in bom.items:
                    assert item.material_code in mat_codes, (
                        f"BOM component {item.material_code} for {product_id} "
                        f"not found in material master"
                    )

    @pytest.mark.asyncio
    async def test_all_routing_work_centers_exist(self, adapter):
        """Every routing work center should appear in the work center list."""
        await adapter.connect()
        wcs = await adapter.sync_work_cells()
        wc_codes = {wc.code for wc in wcs}

        for product_id in ["FG-WIDGET-100", "FG-WIDGET-200", "FG-GADGET-300"]:
            routes = await adapter.sync_routings(product_id)
            for route in routes:
                for step in route.steps:
                    if step.work_center_code:
                        assert step.work_center_code in wc_codes, (
                            f"Work center {step.work_center_code} in routing "
                            f"for {product_id} not found in work center master"
                        )

    @pytest.mark.asyncio
    async def test_all_order_products_exist(self, adapter):
        """Every production order product should appear in the product master."""
        await adapter.connect()
        products = await adapter.sync_products()
        product_codes = {p.code for p in products}

        orders = await adapter.sync_production_orders()
        for order in orders:
            assert order.product_code in product_codes, (
                f"Order {order.erp_reference} references product "
                f"{order.product_code} not in product master"
            )

    @pytest.mark.asyncio
    async def test_all_order_products_have_boms(self, adapter):
        """Every production order product should have at least one BOM."""
        await adapter.connect()
        orders = await adapter.sync_production_orders()
        seen_products = {o.product_code for o in orders}

        for product_code in seen_products:
            boms = await adapter.sync_boms(product_code)
            assert len(boms) > 0, (
                f"Product {product_code} has production orders but no BOM"
            )

    @pytest.mark.asyncio
    async def test_all_order_products_have_routings(self, adapter):
        """Every production order product should have at least one routing."""
        await adapter.connect()
        orders = await adapter.sync_production_orders()
        seen_products = {o.product_code for o in orders}

        for product_code in seen_products:
            routes = await adapter.sync_routings(product_code)
            assert len(routes) > 0, (
                f"Product {product_code} has production orders but no routing"
            )
