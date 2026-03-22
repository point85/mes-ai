"""
Unit tests for Oracle Cloud ERP adapter.

Covers:
- OracleTransformLayer (inbound + outbound field mapping)
- OracleSettings configuration defaults
- OracleClient auth header construction
- OracleInboundAdapter / OracleOutboundAdapter (with mocked HTTP)
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mes.adapters.erp.dtos import (
    BillOfMaterialDTO,
    CompletionReport,
    ConsumptionReport,
    ERPConfirmation,
    MaterialConsumptionDTO,
    MaterialDefinitionDTO,
    ProcessRouteDTO,
    ProductDefinitionDTO,
    ProductionOrderDTO,
    WorkCellDTO,
)
from mes.adapters.erp.oracle.config import OracleSettings
from mes.adapters.erp.oracle.transform import (
    OracleTransformLayer,
    _map_oracle_item_type,
    _map_oracle_operation_type,
    _map_oracle_priority,
    _map_oracle_product_type,
    _parse_oracle_datetime,
    _safe_int,
)


# ═══════════════════════════════════════════════════════════════════
# Transform Layer — Inbound
# ═══════════════════════════════════════════════════════════════════


class TestOracleTransformProductionOrder:
    """Test Oracle → MES production order mapping."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_standard_fields(self):
        oracle_data = {
            "WorkOrderNumber": "WO-100001",
            "ItemNumber": "FG-WIDGET-100",
            "PlannedQuantity": 100,
            "PlannedStartDate": "2026-03-15T08:00:00Z",
            "PlannedCompletionDate": "2026-03-16T16:00:00Z",
            "WorkOrderPriority": "1",
            "UOMCode": "PC",
            "StructureName": "BOM-001",
            "RoutingName": "ROUTE-001",
            "OrganizationCode": "M1",
            "WorkOrderType": "STANDARD",
            "WorkOrderStatusCode": "Released",
            "WorkOrderId": 12345,
        }
        dto = self.tf.to_production_order(oracle_data)
        assert isinstance(dto, ProductionOrderDTO)
        assert dto.erp_reference == "WO-100001"
        assert dto.product_code == "FG-WIDGET-100"
        assert dto.quantity_ordered == 100
        assert dto.priority == 900  # Priority "1" → 900
        assert dto.uom == "PC"
        assert dto.bom_id == "BOM-001"
        assert dto.routing_id == "ROUTE-001"
        assert dto.metadata["oracle_org_code"] == "M1"
        assert dto.metadata["oracle_work_order_type"] == "STANDARD"

    def test_quantity_field_fallback(self):
        oracle_data = {
            "WorkOrderNumber": "WO-200001",
            "ItemNumber": "RAW-STEEL-50",
            "Quantity": 500,
            "UOMCode": "KG",
            "OrganizationCode": "M2",
        }
        dto = self.tf.to_production_order(oracle_data)
        assert dto.erp_reference == "WO-200001"
        assert dto.product_code == "RAW-STEEL-50"
        assert dto.quantity_ordered == 500
        assert dto.uom == "KG"
        assert dto.planned_start is None
        assert dto.planned_end is None

    def test_default_priority(self):
        oracle_data = {
            "WorkOrderNumber": "WO-001",
            "ItemNumber": "MAT-A",
            "PlannedQuantity": 10,
        }
        dto = self.tf.to_production_order(oracle_data)
        assert dto.priority == 500  # None priority → 500


class TestOracleTransformMaterial:
    """Test Oracle → MES material mapping."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_standard_item(self):
        oracle_data = {
            "ItemNumber": "RM-COPPER-WIRE",
            "Description": "Copper Wire 2.5mm",
            "ItemType": "STANDARD",
            "PrimaryUOMCode": "M",
            "LongDescription": "Copper Wire 2.5mm for electrical assemblies",
            "ShelfLifeDays": 365,
            "ItemClass": "Raw Materials",
            "OrganizationCode": "M1",
            "InventoryItemId": 54321,
        }
        dto = self.tf.to_material(oracle_data)
        assert isinstance(dto, MaterialDefinitionDTO)
        assert dto.code == "RM-COPPER-WIRE"
        assert dto.name == "Copper Wire 2.5mm"
        assert dto.material_type == "raw"
        assert dto.uom == "M"
        assert dto.shelf_life_days == 365
        assert dto.description == "Copper Wire 2.5mm for electrical assemblies"

    def test_subassembly(self):
        oracle_data = {
            "ItemNumber": "SF-PCB-ASSY",
            "Description": "PCB Assembly",
            "ItemType": "SUBASSEMBLY",
            "PrimaryUOMCode": "EA",
        }
        dto = self.tf.to_material(oracle_data)
        assert dto.material_type == "semi"

    def test_fallback_description(self):
        oracle_data = {
            "ItemNumber": "MAT-001",
            "ItemDescription": "Test Material",
            "ItemType": "FINISHED_GOOD",
            "PrimaryUOMCode": "PC",
        }
        dto = self.tf.to_material(oracle_data)
        assert dto.code == "MAT-001"
        assert dto.name == "Test Material"
        assert dto.material_type == "finished"


class TestOracleTransformProduct:
    """Test Oracle → MES product mapping."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_finished_good(self):
        oracle_data = {
            "ItemNumber": "FG-WIDGET-A",
            "Description": "Widget Model A",
            "ItemType": "FINISHED_GOOD",
            "RevisionCode": "2.0",
            "ItemStatus": "Active",
        }
        dto = self.tf.to_product(oracle_data)
        assert isinstance(dto, ProductDefinitionDTO)
        assert dto.code == "FG-WIDGET-A"
        assert dto.product_type == "discrete"
        assert dto.version == "2.0"

    def test_configurable_product(self):
        oracle_data = {
            "ItemNumber": "CFG-MOTOR",
            "Description": "Configurable Motor",
            "ItemType": "MODEL",
        }
        dto = self.tf.to_product(oracle_data)
        assert dto.product_type == "configurable"


class TestOracleTransformBOM:
    """Test Oracle → MES BOM mapping."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_bom_with_components(self):
        oracle_data = {
            "ItemNumber": "FG-WIDGET-A",
            "AlternateDesignator": "Primary",
            "StructureName": "STR-001",
            "StructureType": "Manufacturing",
            "OrganizationCode": "M1",
            "Component": [
                {
                    "ComponentItemNumber": "RM-STEEL",
                    "ComponentQuantity": 2.5,
                    "UOMCode": "KG",
                    "ComponentSequenceNumber": 10,
                },
                {
                    "ComponentItemNumber": "RM-SCREW-M4",
                    "ComponentQuantity": 8,
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": 20,
                },
            ],
        }
        dto = self.tf.to_bom(oracle_data)
        assert isinstance(dto, BillOfMaterialDTO)
        assert dto.product_code == "FG-WIDGET-A"
        assert dto.version == "Primary"
        assert len(dto.items) == 2
        assert dto.items[0].material_code == "RM-STEEL"
        assert dto.items[0].quantity == 2.5
        assert dto.items[1].sequence == 20

    def test_bom_empty_components(self):
        oracle_data = {"ItemNumber": "FG-X", "Component": []}
        dto = self.tf.to_bom(oracle_data)
        assert len(dto.items) == 0

    def test_bom_fallback_component_fields(self):
        oracle_data = {
            "ItemNumber": "FG-Y",
            "Component": [
                {
                    "ComponentItem": "RM-BOLT",
                    "Quantity": 4,
                },
            ],
        }
        dto = self.tf.to_bom(oracle_data)
        assert dto.items[0].material_code == "RM-BOLT"
        assert dto.items[0].quantity == 4.0


class TestOracleTransformRouting:
    """Test Oracle → MES routing mapping."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_routing_with_operations(self):
        oracle_data = {
            "ItemNumber": "FG-WIDGET-A",
            "RoutingName": "ROUTE-001",
            "AlternateRoutingDesignator": "01",
            "OrganizationCode": "M1",
            "Operation": [
                {
                    "OperationSequenceNumber": 20,
                    "OperationName": "Assembly",
                    "OperationType": "PRODUCTION",
                    "WorkCenterName": "WC-ASSY-01",
                    "OperationDescription": "Final assembly step",
                },
                {
                    "OperationSequenceNumber": 10,
                    "OperationName": "Cutting",
                    "OperationType": "PRODUCTION",
                    "WorkCenterName": "WC-CUT-01",
                    "OperationDescription": "Metal cutting",
                },
            ],
        }
        dto = self.tf.to_routing(oracle_data)
        assert isinstance(dto, ProcessRouteDTO)
        assert dto.product_code == "FG-WIDGET-A"
        assert dto.name == "ROUTE-001"
        # Steps should be sorted by sequence
        assert len(dto.steps) == 2
        assert dto.steps[0].sequence == 10
        assert dto.steps[0].name == "Cutting"
        assert dto.steps[1].sequence == 20

    def test_inspection_step_type(self):
        oracle_data = {
            "ItemNumber": "X",
            "Operation": [
                {
                    "OperationSequenceNumber": 10,
                    "OperationName": "QC Inspection",
                    "OperationType": "INSPECTION",
                    "WorkCenterName": "WC-QC-01",
                },
            ],
        }
        dto = self.tf.to_routing(oracle_data)
        assert dto.steps[0].step_type == "inspection"

    def test_routing_sequence_fallback(self):
        oracle_data = {
            "ItemNumber": "X",
            "Operation": [
                {
                    "OperationSequence": 30,
                    "OperationDescription": "Testing",
                    "WorkCenter": "WC-TEST-01",
                },
            ],
        }
        dto = self.tf.to_routing(oracle_data)
        assert dto.steps[0].sequence == 30
        assert dto.steps[0].work_center_code == "WC-TEST-01"


class TestOracleTransformWorkCell:
    """Test Oracle → MES work cell mapping."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_work_center(self):
        oracle_data = {
            "WorkCenterName": "WC-ASSY-01",
            "Description": "Assembly Station 01",
            "OrganizationCode": "M1",
            "WorkCenterType": "Assembly",
            "ResourceCount": "5",
        }
        dto = self.tf.to_work_cell(oracle_data)
        assert isinstance(dto, WorkCellDTO)
        assert dto.code == "WC-ASSY-01"
        assert dto.name == "Assembly Station 01"
        assert dto.area_code == "M1"

    def test_fallback_fields(self):
        oracle_data = {
            "WorkCenter": "WC-100",
            "WorkCenterDescription": "Work Center 100",
            "OrganizationCode": "M2",
        }
        dto = self.tf.to_work_cell(oracle_data)
        assert dto.code == "WC-100"
        assert dto.name == "Work Center 100"
        assert dto.area_code == "M2"


# ═══════════════════════════════════════════════════════════════════
# Transform Layer — Outbound
# ═══════════════════════════════════════════════════════════════════


class TestOracleTransformOutbound:
    """Test MES → Oracle outbound transforms."""

    def setup_method(self):
        self.tf = OracleTransformLayer()

    def test_completion_report(self):
        report = CompletionReport(
            erp_reference="WO-100001",
            qty_good=95,
            qty_reject=5,
            uom="PC",
            step_id="20",
            completed_at=datetime(2026, 3, 15, 16, 0, 0, tzinfo=timezone.utc),
        )
        payload = self.tf.from_completion(report)
        assert payload["WorkOrderNumber"] == "WO-100001"
        assert payload["CompletedQuantity"] == 95
        assert payload["RejectedQuantity"] == 5
        assert payload["OperationSequenceNumber"] == "20"
        assert payload["UOMCode"] == "PC"
        assert "TransactionDate" in payload

    def test_completion_report_default_operation(self):
        report = CompletionReport(
            erp_reference="WO-001",
            qty_good=10,
            qty_reject=0,
        )
        payload = self.tf.from_completion(report)
        assert payload["OperationSequenceNumber"] == "10"  # Default

    def test_consumption_report(self):
        report = ConsumptionReport(
            erp_reference="WO-100001",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-STEEL",
                    quantity=2.5,
                    uom="KG",
                    lot_number="LOT-001",
                ),
            ],
        )
        payload = self.tf.from_consumption(report)
        assert payload["WorkOrderNumber"] == "WO-100001"
        assert len(payload["MaterialTransactions"]) == 1
        item = payload["MaterialTransactions"][0]
        assert item["ItemNumber"] == "RM-STEEL"
        assert item["TransactionQuantity"] == 2.5
        assert item["LotNumber"] == "LOT-001"
        assert item["TransactionType"] == "WIP_ISSUE"

    def test_consumption_no_lot(self):
        report = ConsumptionReport(
            erp_reference="WO-002",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-WIRE",
                    quantity=10.0,
                ),
            ],
        )
        payload = self.tf.from_consumption(report)
        assert payload["MaterialTransactions"][0]["LotNumber"] == ""


# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════


class TestParseOracleDatetime:
    def test_iso8601(self):
        result = _parse_oracle_datetime("2026-03-15T08:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 15

    def test_iso8601_with_offset(self):
        result = _parse_oracle_datetime("2026-03-15T08:00:00+02:00")
        assert result is not None

    def test_none(self):
        assert _parse_oracle_datetime(None) is None

    def test_empty_string(self):
        assert _parse_oracle_datetime("") is None

    def test_invalid_format(self):
        assert _parse_oracle_datetime("not-a-date") is None


class TestMapOraclePriority:
    def test_all_levels(self):
        assert _map_oracle_priority("1") == 900
        assert _map_oracle_priority("2") == 700
        assert _map_oracle_priority("3") == 500
        assert _map_oracle_priority("4") == 300
        assert _map_oracle_priority("5") == 100

    def test_default(self):
        assert _map_oracle_priority("X") == 500
        assert _map_oracle_priority("") == 500

    def test_none(self):
        assert _map_oracle_priority(None) == 500

    def test_integer_value(self):
        assert _map_oracle_priority(2) == 700


class TestMapOracleItemType:
    def test_known_types(self):
        assert _map_oracle_item_type("STANDARD") == "raw"
        assert _map_oracle_item_type("RAW_MATERIAL") == "raw"
        assert _map_oracle_item_type("SUBASSEMBLY") == "semi"
        assert _map_oracle_item_type("FINISHED_GOOD") == "finished"
        assert _map_oracle_item_type("PURCHASED") == "raw"
        assert _map_oracle_item_type("EXPENSE") == "consumable"
        assert _map_oracle_item_type("PHANTOM") == "phantom"

    def test_unknown(self):
        assert _map_oracle_item_type("XXXX") == "raw"


class TestMapOracleProductType:
    def test_known_types(self):
        assert _map_oracle_product_type("STANDARD") == "discrete"
        assert _map_oracle_product_type("FINISHED_GOOD") == "discrete"
        assert _map_oracle_product_type("SUBASSEMBLY") == "semi_finished"
        assert _map_oracle_product_type("MODEL") == "configurable"
        assert _map_oracle_product_type("PROCESS") == "process"

    def test_unknown(self):
        assert _map_oracle_product_type("ZZZZ") == "discrete"


class TestMapOracleOperationType:
    def test_production(self):
        assert _map_oracle_operation_type("PRODUCTION") == "production"
        assert _map_oracle_operation_type("") == "production"

    def test_inspection(self):
        assert _map_oracle_operation_type("INSPECTION") == "inspection"
        assert _map_oracle_operation_type("QUALITY_CHECK") == "inspection"

    def test_maintenance(self):
        assert _map_oracle_operation_type("MAINTENANCE") == "maintenance"


class TestOracleSafeInt:
    def test_valid(self):
        assert _safe_int("365") == 365
        assert _safe_int(100) == 100

    def test_none(self):
        assert _safe_int(None) is None

    def test_invalid(self):
        assert _safe_int("abc") is None


# ═══════════════════════════════════════════════════════════════════
# OracleSettings config defaults
# ═══════════════════════════════════════════════════════════════════


class TestOracleSettings:
    def test_defaults(self):
        s = OracleSettings()
        assert s.ORACLE_BUSINESS_UNIT == "Manufacturing BU"
        assert s.ORACLE_ORGANIZATION_CODE == "M1"
        assert s.ORACLE_PLANT_CODE == "M1"
        assert s.ORACLE_REQUEST_TIMEOUT_SEC == 30
        assert s.ORACLE_PAGE_SIZE == 100

    def test_api_paths(self):
        s = OracleSettings()
        assert "workOrders" in s.ORACLE_WORK_ORDER_PATH
        assert "inventoryItemsV2" in s.ORACLE_ITEM_PATH
        assert "itemStructures" in s.ORACLE_STRUCTURE_PATH
        assert "workCenters" in s.ORACLE_WORK_CENTER_PATH
        assert "workOrderOperations" in s.ORACLE_ROUTING_PATH
        assert "workOrderCompletions" in s.ORACLE_COMPLETION_PATH
        assert "inventoryTransactions" in s.ORACLE_TRANSACTION_PATH
        assert "qualityResults" in s.ORACLE_QUALITY_PATH


# ═══════════════════════════════════════════════════════════════════
# Client — header construction
# ═══════════════════════════════════════════════════════════════════


class TestOracleClientHeaders:
    def test_oauth2_header(self):
        from mes.adapters.erp.oracle.client import OracleClient

        client = OracleClient()
        client._access_token = "test-token-123"
        with patch("mes.adapters.erp.oracle.client.settings") as mock_settings:
            mock_settings.ERP_AUTH_TYPE = "oauth2"
            headers = client._build_headers()
        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["Accept"] == "application/json"

    def test_basic_header(self):
        from mes.adapters.erp.oracle.client import OracleClient

        client = OracleClient()
        with patch("mes.adapters.erp.oracle.client.settings") as mock_settings:
            mock_settings.ERP_AUTH_TYPE = "basic"
            mock_settings.ERP_CLIENT_ID = "user"
            mock_settings.ERP_CLIENT_SECRET = "pass"
            headers = client._build_headers()
        expected = base64.b64encode(b"user:pass").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_api_key_header(self):
        from mes.adapters.erp.oracle.client import OracleClient

        client = OracleClient()
        with patch("mes.adapters.erp.oracle.client.settings") as mock_settings:
            mock_settings.ERP_AUTH_TYPE = "api_key"
            mock_settings.ERP_CLIENT_SECRET = "my-api-key-123"
            headers = client._build_headers()
        assert headers["X-Api-Key"] == "my-api-key-123"


# ═══════════════════════════════════════════════════════════════════
# Adapter — Inbound (with mocked HTTP)
# ═══════════════════════════════════════════════════════════════════


class TestOracleInboundAdapter:
    """Test OracleInboundAdapter with a mocked OracleClient."""

    @pytest.fixture()
    def adapter(self):
        from mes.adapters.erp.oracle.adapter import OracleInboundAdapter

        a = OracleInboundAdapter()
        a._client = MagicMock()
        a._client.connect = AsyncMock()
        a._client.disconnect = AsyncMock()
        a._client.health_check = AsyncMock(return_value=True)
        return a

    @pytest.mark.asyncio()
    async def test_connect_disconnect(self, adapter):
        await adapter.connect()
        adapter._client.connect.assert_awaited_once()
        await adapter.disconnect()
        adapter._client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_health_check(self, adapter):
        result = await adapter.health_check()
        assert result is True

    @pytest.mark.asyncio()
    async def test_sync_production_orders(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "WorkOrderNumber": "WO-100001",
                "ItemNumber": "FG-WIDGET",
                "PlannedQuantity": 50,
                "OrganizationCode": "M1",
            },
        ])
        orders = await adapter.sync_production_orders()
        assert len(orders) == 1
        assert orders[0].erp_reference == "WO-100001"
        assert orders[0].quantity_ordered == 50

    @pytest.mark.asyncio()
    async def test_sync_production_orders_with_since(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[])
        since = datetime(2026, 3, 1, tzinfo=timezone.utc)
        orders = await adapter.sync_production_orders(since=since)
        assert len(orders) == 0
        # Verify filter includes LastUpdateDate
        call_args = adapter._client.get_list.call_args
        assert "LastUpdateDate" in call_args.kwargs.get("q_filter", "")

    @pytest.mark.asyncio()
    async def test_sync_materials(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "ItemNumber": "RM-STEEL",
                "Description": "Cold Rolled Steel",
                "ItemType": "STANDARD",
                "PrimaryUOMCode": "KG",
            },
        ])
        materials = await adapter.sync_materials()
        assert len(materials) == 1
        assert materials[0].code == "RM-STEEL"
        assert materials[0].material_type == "raw"

    @pytest.mark.asyncio()
    async def test_sync_products(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "ItemNumber": "FG-MOTOR-A",
                "Description": "Motor A",
                "ItemType": "FINISHED_GOOD",
            },
        ])
        products = await adapter.sync_products()
        assert len(products) == 1
        assert products[0].code == "FG-MOTOR-A"

    @pytest.mark.asyncio()
    async def test_sync_boms(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "ItemNumber": "FG-X",
                "AlternateDesignator": "01",
                "Component": [
                    {
                        "ComponentItemNumber": "RM-A",
                        "ComponentQuantity": 3,
                        "UOMCode": "EA",
                        "ComponentSequenceNumber": 10,
                    },
                ],
            },
        ])
        boms = await adapter.sync_boms("FG-X")
        assert len(boms) == 1
        assert len(boms[0].items) == 1
        assert boms[0].items[0].material_code == "RM-A"

    @pytest.mark.asyncio()
    async def test_sync_routings(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "ItemNumber": "FG-X",
                "RoutingName": "R-001",
                "Operation": [
                    {
                        "OperationSequenceNumber": 10,
                        "OperationName": "Cut",
                        "WorkCenterName": "WC-01",
                    },
                ],
            },
        ])
        routings = await adapter.sync_routings("FG-X")
        assert len(routings) == 1
        assert routings[0].steps[0].name == "Cut"

    @pytest.mark.asyncio()
    async def test_sync_work_cells(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "WorkCenterName": "WC-ASSY-01",
                "Description": "Assembly 01",
                "OrganizationCode": "M1",
            },
        ])
        cells = await adapter.sync_work_cells()
        assert len(cells) == 1
        assert cells[0].code == "WC-ASSY-01"


# ═══════════════════════════════════════════════════════════════════
# Adapter — Outbound (with mocked HTTP)
# ═══════════════════════════════════════════════════════════════════


class TestOracleOutboundAdapter:
    """Test OracleOutboundAdapter with a mocked OracleClient."""

    @pytest.fixture()
    def adapter(self):
        from mes.adapters.erp.oracle.adapter import OracleOutboundAdapter

        a = OracleOutboundAdapter()
        a._client = MagicMock()
        a._client.connect = AsyncMock()
        a._client.disconnect = AsyncMock()
        a._client.health_check = AsyncMock(return_value=True)
        a._client.post = AsyncMock(return_value={"CompletionTransactionId": "ORA-COMP-001"})
        return a

    @pytest.mark.asyncio()
    async def test_report_completion(self, adapter):
        result = await adapter.report_completion(
            order_id="WO-001",
            qty_good=95,
            qty_reject=5,
            step_id="20",
        )
        assert isinstance(result, ERPConfirmation)
        assert result.success is True
        assert result.erp_doc_number == "ORA-COMP-001"
        # Verify POST was called
        adapter._client.post.assert_awaited_once()
        payload = adapter._client.post.call_args.args[1]
        assert payload["WorkOrderNumber"] == "WO-001"
        assert payload["CompletedQuantity"] == 95

    @pytest.mark.asyncio()
    async def test_report_consumption(self, adapter):
        adapter._client.post = AsyncMock(return_value={"TransactionHeaderId": "TXN-001"})
        result = await adapter.report_consumption(
            order_id="WO-001",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-STEEL",
                    quantity=2.5,
                    uom="KG",
                ),
            ],
        )
        assert result.success is True
        assert result.erp_doc_number == "TXN-001"

    @pytest.mark.asyncio()
    async def test_report_scrap(self, adapter):
        result = await adapter.report_scrap(
            order_id="WO-001",
            qty_scrapped=3,
            reason_code="DEFECT",
        )
        assert result.success is True
        payload = adapter._client.post.call_args.args[1]
        assert payload["RejectedQuantity"] == 3
        assert payload["ScrapReasonCode"] == "DEFECT"

    @pytest.mark.asyncio()
    async def test_report_labor(self, adapter):
        adapter._client.post = AsyncMock(return_value={"TransactionHeaderId": "TXN-LAB-001"})
        result = await adapter.report_labor(
            order_id="WO-001",
            operator_id="OP-001",
            duration_minutes=120.0,
        )
        assert result.success is True
        payload = adapter._client.post.call_args.args[1]
        assert payload["ResourceUsage"] == 120.0
        assert payload["ResourceCode"] == "OP-001"

    @pytest.mark.asyncio()
    async def test_report_downtime(self, adapter):
        adapter._client.post = AsyncMock(return_value={"TransactionHeaderId": "TXN-DT-001"})
        started = datetime(2026, 3, 15, 8, 0, 0, tzinfo=timezone.utc)
        result = await adapter.report_downtime(
            equipment_id="EQ-001",
            duration_minutes=30.0,
            reason_code="MAINT",
            started_at=started,
        )
        assert result.success is True
        payload = adapter._client.post.call_args.args[1]
        assert payload["ResourceCode"] == "EQ-001"
        assert payload["ReasonCode"] == "MAINT"

    @pytest.mark.asyncio()
    async def test_report_quality_result(self, adapter):
        adapter._client.post = AsyncMock(return_value={"QualityResultId": "QR-001"})
        result = await adapter.report_quality_result(
            order_id="WO-001",
            test_id="TEST-001",
            result="PASS",
            details={"measurement": 5.0},
        )
        assert result.success is True
        assert result.erp_doc_number == "QR-001"


