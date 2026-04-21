"""
Unit tests for SAP S/4HANA ERP adapter.

Covers:
- SAPS4HANATransformLayer (inbound + outbound field mapping)
- SAPSettings configuration defaults
- SAPS4HANAClient auth header construction
- SAPS4HANAInboundAdapter / SAPS4HANAOutboundAdapter (with mocked HTTP)
"""

from __future__ import annotations

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
from mes.adapters.erp.sap_s4hana.config import SAPSettings
from mes.adapters.erp.sap_s4hana.transform import (
    SAPS4HANATransformLayer,
    _map_sap_material_type,
    _map_sap_priority,
    _map_sap_product_type,
    _parse_sap_datetime,
    _safe_int,
)


# ═══════════════════════════════════════════════════════════════════
# Transform Layer — Inbound
# ═══════════════════════════════════════════════════════════════════


class TestSAPTransformProductionOrder:
    """Test SAP → MES production order mapping."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_odata_v4_fields(self):
        sap_data = {
            "ManufacturingOrder": "000001234567",
            "Material": "FG-WIDGET-100",
            "TotalQuantity": "100",
            "MfgOrderPlannedStartDate": "2026-03-15T08:00:00Z",
            "MfgOrderPlannedEndDate": "2026-03-16T16:00:00Z",
            "MfgOrderPriority": "1",
            "ProductionUnit": "PC",
            "BillOfMaterial": "00012345",
            "ProductionRouting": "00056789",
            "ProductionPlant": "1000",
            "ManufacturingOrderType": "PP01",
            "MfgOrderStatus": "REL",
            "MRPController": "001",
        }
        dto = self.tf.to_production_order(sap_data)
        assert isinstance(dto, ProductionOrderDTO)
        assert dto.erp_reference == "000001234567"
        assert dto.product_code == "FG-WIDGET-100"
        assert dto.quantity_ordered == 100
        assert dto.priority == 900  # SAP priority "1" → 900
        assert dto.uom == "PC"
        assert dto.bom_id == "00012345"
        assert dto.routing_id == "00056789"
        assert dto.metadata["sap_plant"] == "1000"
        assert dto.metadata["sap_order_type"] == "PP01"

    def test_legacy_field_names(self):
        sap_data = {
            "AUFNR": "000009999999",
            "MATNR": "RAW-STEEL-50",
            "GAMNG": "500",
            "GSTRP": None,
            "GLTRP": None,
            "GMEIN": "KG",
            "WERKS": "2000",
            "AUART": "PP02",
        }
        dto = self.tf.to_production_order(sap_data)
        assert dto.erp_reference == "000009999999"
        assert dto.product_code == "RAW-STEEL-50"
        assert dto.quantity_ordered == 500
        assert dto.uom == "kg"
        assert dto.planned_start is None
        assert dto.planned_end is None

    def test_default_priority(self):
        sap_data = {
            "ManufacturingOrder": "PO-001",
            "Material": "MAT-A",
            "TotalQuantity": "10",
        }
        dto = self.tf.to_production_order(sap_data)
        # SAP default priority is "2" (High → 700)
        assert dto.priority == 700


class TestSAPTransformMaterial:
    """Test SAP → MES material mapping."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_raw_material(self):
        sap_data = {
            "Material": "RM-COPPER-WIRE",
            "MaterialName": "Copper Wire 2.5mm",
            "MaterialType": "ROH",
            "BaseUnit": "M",
            "MaterialDescription": "Copper Wire 2.5mm",
            "MaximumStoragePeriod": "365",
            "MaterialGroup": "001",
            "Plant": "1000",
        }
        dto = self.tf.to_material(sap_data)
        assert isinstance(dto, MaterialDefinitionDTO)
        assert dto.code == "RM-COPPER-WIRE"
        assert dto.name == "Copper Wire 2.5mm"
        assert dto.material_type == "raw"
        assert dto.uom == "m"
        assert dto.revision is None
        assert dto.shelf_life_days == 365

    def test_semi_finished(self):
        sap_data = {
            "Material": "SF-PCB-ASSY",
            "MaterialName": "PCB Assembly",
            "MaterialType": "HALB",
            "BaseUnit": "EA",
        }
        dto = self.tf.to_material(sap_data)
        assert dto.material_type == "semi"

    def test_legacy_fields(self):
        sap_data = {
            "MATNR": "MAT-001",
            "MAKTX": "Test Material",
            "MTART": "FERT",
            "MEINS": "PC",
        }
        dto = self.tf.to_material(sap_data)
        assert dto.code == "MAT-001"
        assert dto.material_type == "finished"


class TestSAPTransformProduct:
    """Test SAP → MES product mapping."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_finished_product(self):
        sap_data = {
            "Product": "FG-WIDGET-A",
            "ProductDescription": "Widget Model A",
            "MaterialType": "FERT",
            "MaterialRevisionLevel": "2.0",
            "IndustrySector": "M",
        }
        dto = self.tf.to_product(sap_data)
        assert isinstance(dto, ProductDefinitionDTO)
        assert dto.code == "FG-WIDGET-A"
        assert dto.product_type == "discrete"
        assert dto.version == "2.0"

    def test_configurable_product(self):
        sap_data = {
            "Product": "CFG-MOTOR",
            "ProductDescription": "Configurable Motor",
            "MaterialType": "KMAT",
        }
        dto = self.tf.to_product(sap_data)
        assert dto.product_type == "configurable"


class TestSAPTransformBOM:
    """Test SAP → MES BOM mapping."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_bom_with_items(self):
        sap_data = {
            "Material": "FG-WIDGET-A",
            "BillOfMaterialVariant": "01",
            "BillOfMaterial": "00012345",
            "BillOfMaterialVariantUsage": "1",
            "to_BOMItem": [
                {
                    "BillOfMaterialComponent": "RM-STEEL",
                    "BillOfMaterialItemQuantity": "2.5",
                    "BillOfMaterialItemUnit": "KG",
                    "BillOfMaterialItemNumber": "10",
                },
                {
                    "BillOfMaterialComponent": "RM-SCREW-M4",
                    "BillOfMaterialItemQuantity": "8",
                    "BillOfMaterialItemUnit": "EA",
                    "BillOfMaterialItemNumber": "20",
                },
            ],
        }
        dto = self.tf.to_bom(sap_data)
        assert isinstance(dto, BillOfMaterialDTO)
        assert dto.product_code == "FG-WIDGET-A"
        assert dto.version == "01"
        assert len(dto.items) == 2
        assert dto.items[0].material_code == "RM-STEEL"
        assert dto.items[0].quantity == 2.5
        assert dto.items[1].sequence == 20

    def test_bom_empty_items(self):
        sap_data = {"Material": "FG-X", "to_BOMItem": []}
        dto = self.tf.to_bom(sap_data)
        assert len(dto.items) == 0


class TestSAPTransformRouting:
    """Test SAP → MES routing mapping."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_routing_with_operations(self):
        sap_data = {
            "Material": "FG-WIDGET-A",
            "ProductionRoutingGroup": "ROUTE-001",
            "ProductionRoutingGroupCounter": "01",
            "Plant": "1000",
            "to_Operation": [
                {
                    "OperationNumber": "0020",
                    "OperationText": "Assembly",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-ASSY-01",
                },
                {
                    "OperationNumber": "0010",
                    "OperationText": "Cutting",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-CUT-01",
                },
            ],
        }
        dto = self.tf.to_routing(sap_data)
        assert isinstance(dto, ProcessRouteDTO)
        assert dto.product_code == "FG-WIDGET-A"
        assert dto.name == "ROUTE-001"
        # Steps should be sorted by sequence
        assert len(dto.steps) == 2
        assert dto.steps[0].sequence == 10
        assert dto.steps[0].name == "Cutting"
        assert dto.steps[1].sequence == 20

    def test_inspection_step_type(self):
        sap_data = {
            "Material": "X",
            "to_Operation": [
                {
                    "OperationNumber": "0010",
                    "OperationText": "QC Inspection",
                    "OperationControlProfile": "QM01",
                    "WorkCenter": "WC-QC-01",
                },
            ],
        }
        dto = self.tf.to_routing(sap_data)
        assert dto.steps[0].step_type == "inspection"


class TestSAPTransformWorkCell:
    """Test SAP → MES work cell mapping."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_work_center(self):
        sap_data = {
            "WorkCenter": "WC-ASSY-01",
            "WorkCenterText": "Assembly Station 01",
            "Plant": "1000",
            "WorkCenterCategoryCode": "0001",
            "Capacity": "10",
        }
        dto = self.tf.to_work_cell(sap_data)
        assert isinstance(dto, WorkCellDTO)
        assert dto.code == "WC-ASSY-01"
        assert dto.name == "Assembly Station 01"
        assert dto.area_code == "1000"

    def test_legacy_fields(self):
        sap_data = {
            "ARBPL": "WC-100",
            "KTEXT": "Work Center 100",
            "WERKS": "2000",
        }
        dto = self.tf.to_work_cell(sap_data)
        assert dto.code == "WC-100"
        assert dto.area_code == "2000"


# ═══════════════════════════════════════════════════════════════════
# Transform Layer — Outbound
# ═══════════════════════════════════════════════════════════════════


class TestSAPTransformOutbound:
    """Test MES → SAP outbound transforms."""

    def setup_method(self):
        self.tf = SAPS4HANATransformLayer()

    def test_completion_report(self):
        report = CompletionReport(
            erp_reference="000001234567",
            qty_good=95,
            qty_reject=5,
            uom="PC",
            step_id="0010",
            completed_at=datetime(2026, 3, 15, 16, 0, 0, tzinfo=timezone.utc),
        )
        payload = self.tf.from_completion(report)
        assert payload["OrderID"] == "000001234567"
        assert payload["ConfirmationYieldQuantity"] == "95"
        assert payload["ConfirmationScrapQuantity"] == "5"
        assert payload["OrderOperation"] == "0010"
        assert payload["ConfirmationUnit"] == "PC"
        assert "PostingDate" in payload

    def test_completion_report_default_operation(self):
        report = CompletionReport(
            erp_reference="PO-001",
            qty_good=10,
            qty_reject=0,
        )
        payload = self.tf.from_completion(report)
        assert payload["OrderOperation"] == "0010"  # Default

    def test_consumption_report(self):
        report = ConsumptionReport(
            erp_reference="000001234567",
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
        assert payload["OrderID"] == "000001234567"
        assert len(payload["GoodsMovementItems"]) == 1
        item = payload["GoodsMovementItems"][0]
        assert item["Material"] == "RM-STEEL"
        assert item["Quantity"] == "2.5"
        assert item["Batch"] == "LOT-001"
        assert item["GoodsMovementType"] == "261"

    def test_consumption_no_lot(self):
        report = ConsumptionReport(
            erp_reference="PO-002",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-WIRE",
                    quantity=10.0,
                ),
            ],
        )
        payload = self.tf.from_consumption(report)
        assert payload["GoodsMovementItems"][0]["Batch"] == ""


# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════


class TestParseSAPDatetime:
    def test_iso8601(self):
        result = _parse_sap_datetime("2026-03-15T08:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 15

    def test_iso8601_with_offset(self):
        result = _parse_sap_datetime("2026-03-15T08:00:00+02:00")
        assert result is not None

    def test_legacy_date_format(self):
        # /Date(1742025600000)/ = 2025-03-15T12:00:00 UTC (approx)
        result = _parse_sap_datetime("/Date(1742025600000)/")
        assert isinstance(result, datetime)

    def test_none(self):
        assert _parse_sap_datetime(None) is None

    def test_empty_string(self):
        assert _parse_sap_datetime("") is None

    def test_invalid_format(self):
        assert _parse_sap_datetime("not-a-date") is None


class TestMapSAPPriority:
    def test_all_levels(self):
        assert _map_sap_priority("1") == 900
        assert _map_sap_priority("2") == 700
        assert _map_sap_priority("3") == 500
        assert _map_sap_priority("4") == 300
        assert _map_sap_priority("5") == 100

    def test_default(self):
        assert _map_sap_priority("X") == 500
        assert _map_sap_priority("") == 500


class TestMapSAPMaterialType:
    def test_known_types(self):
        assert _map_sap_material_type("ROH") == "raw"
        assert _map_sap_material_type("HALB") == "semi"
        assert _map_sap_material_type("FERT") == "finished"
        assert _map_sap_material_type("HIBE") == "consumable"
        assert _map_sap_material_type("VERP") == "packaging"
        assert _map_sap_material_type("ERSA") == "spare"

    def test_unknown(self):
        assert _map_sap_material_type("XXXX") == "raw"


class TestMapSAPProductType:
    def test_known_types(self):
        assert _map_sap_product_type("FERT") == "discrete"
        assert _map_sap_product_type("HALB") == "semi_finished"
        assert _map_sap_product_type("KMAT") == "configurable"
        assert _map_sap_product_type("PROC") == "process"

    def test_unknown(self):
        assert _map_sap_product_type("ZZZZ") == "discrete"


class TestSafeInt:
    def test_valid(self):
        assert _safe_int("365") == 365
        assert _safe_int(100) == 100

    def test_none(self):
        assert _safe_int(None) is None

    def test_invalid(self):
        assert _safe_int("abc") is None


# ═══════════════════════════════════════════════════════════════════
# SAPSettings config defaults
# ═══════════════════════════════════════════════════════════════════


class TestSAPSettings:
    def test_defaults(self):
        s = SAPSettings()
        assert s.SAP_COMPANY_CODE == "1000"
        assert s.SAP_PLANT == "1000"
        assert s.SAP_STORAGE_LOCATION == "0001"
        assert s.SAP_REQUEST_TIMEOUT_SEC == 30
        assert s.SAP_PAGE_SIZE == 100

    def test_api_paths(self):
        s = SAPSettings()
        assert "api_production_order" in s.SAP_PRODUCTION_ORDER_PATH
        assert "api_material" in s.SAP_MATERIAL_PATH
        assert "api_product" in s.SAP_PRODUCT_PATH
        assert "api_bill_of_material" in s.SAP_BOM_PATH
        assert "api_production_routing" in s.SAP_ROUTING_PATH
        assert "api_work_centers" in s.SAP_WORK_CENTER_PATH
        assert "api_prod_order_confirmation" in s.SAP_CONFIRMATION_PATH


# ═══════════════════════════════════════════════════════════════════
# Client — header construction
# ═══════════════════════════════════════════════════════════════════


class TestSAPClientHeaders:
    def test_oauth2_header(self):
        from mes.adapters.erp.sap_s4hana.client import SAPS4HANAClient

        client = SAPS4HANAClient()
        client._access_token = "test-token-123"
        with patch("mes.adapters.erp.sap_s4hana.client.settings") as mock_settings:
            mock_settings.ERP_AUTH_TYPE = "oauth2"
            headers = client._build_headers()
        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["Accept"] == "application/json"

    def test_basic_header(self):
        from mes.adapters.erp.sap_s4hana.client import SAPS4HANAClient

        client = SAPS4HANAClient()
        with patch("mes.adapters.erp.sap_s4hana.client.settings") as mock_settings:
            mock_settings.ERP_AUTH_TYPE = "basic"
            mock_settings.ERP_CLIENT_ID = "user"
            mock_settings.ERP_CLIENT_SECRET = "pass"
            headers = client._build_headers()
        import base64
        expected = base64.b64encode(b"user:pass").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_api_key_header(self):
        from mes.adapters.erp.sap_s4hana.client import SAPS4HANAClient

        client = SAPS4HANAClient()
        with patch("mes.adapters.erp.sap_s4hana.client.settings") as mock_settings:
            mock_settings.ERP_AUTH_TYPE = "api_key"
            mock_settings.ERP_CLIENT_SECRET = "my-api-key-123"
            with patch("mes.adapters.erp.sap_s4hana.client.sap_settings") as mock_sap:
                mock_sap.SAP_API_KEY_HEADER = "APIKey"
                headers = client._build_headers()
        assert headers["APIKey"] == "my-api-key-123"


# ═══════════════════════════════════════════════════════════════════
# Adapter — Inbound (with mocked HTTP)
# ═══════════════════════════════════════════════════════════════════


class TestSAPInboundAdapter:
    """Test SAPS4HANAInboundAdapter with a mocked SAPS4HANAClient."""

    @pytest.fixture()
    def adapter(self):
        from mes.adapters.erp.sap_s4hana.adapter import SAPS4HANAInboundAdapter

        a = SAPS4HANAInboundAdapter()
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
    async def test_sync_operations_requests(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "ManufacturingOrder": "000001000001",
                "Material": "FG-WIDGET",
                "TotalQuantity": "50",
                "ProductionPlant": "1000",
            },
        ])
        orders = await adapter.sync_operations_requests()
        assert len(orders) == 1
        assert orders[0].erp_reference == "000001000001"
        assert orders[0].quantity_ordered == 50

    @pytest.mark.asyncio()
    async def test_sync_operations_requests_with_since(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[])
        since = datetime(2026, 3, 1, tzinfo=timezone.utc)
        orders = await adapter.sync_operations_requests(since=since)
        assert len(orders) == 0
        # Verify filter includes LastChangeDateTime
        call_args = adapter._client.get_list.call_args
        assert "LastChangeDateTime" in call_args.kwargs.get("filter_expr", "")

    @pytest.mark.asyncio()
    async def test_sync_materials(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "Material": "RM-STEEL",
                "MaterialName": "Cold Rolled Steel",
                "MaterialType": "ROH",
                "BaseUnit": "KG",
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
                "Product": "FG-MOTOR-A",
                "ProductDescription": "Motor A",
                "MaterialType": "FERT",
            },
        ])
        products = await adapter.sync_products()
        assert len(products) == 1
        assert products[0].code == "FG-MOTOR-A"

    @pytest.mark.asyncio()
    async def test_sync_boms(self, adapter):
        adapter._client.get_list = AsyncMock(return_value=[
            {
                "Material": "FG-X",
                "BillOfMaterialVariant": "01",
                "to_BOMItem": [
                    {
                        "BillOfMaterialComponent": "RM-A",
                        "BillOfMaterialItemQuantity": "3",
                        "BillOfMaterialItemUnit": "EA",
                        "BillOfMaterialItemNumber": "10",
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
                "Material": "FG-X",
                "ProductionRoutingGroup": "R-001",
                "to_Operation": [
                    {
                        "OperationNumber": "0010",
                        "OperationText": "Cut",
                        "WorkCenter": "WC-01",
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
                "WorkCenter": "WC-ASSY-01",
                "WorkCenterText": "Assembly 01",
                "Plant": "1000",
            },
        ])
        cells = await adapter.sync_work_cells()
        assert len(cells) == 1
        assert cells[0].code == "WC-ASSY-01"


# ═══════════════════════════════════════════════════════════════════
# Adapter — Outbound (with mocked HTTP)
# ═══════════════════════════════════════════════════════════════════


class TestSAPOutboundAdapter:
    """Test SAPS4HANAOutboundAdapter with a mocked SAPS4HANAClient."""

    @pytest.fixture()
    def adapter(self):
        from mes.adapters.erp.sap_s4hana.adapter import SAPS4HANAOutboundAdapter

        a = SAPS4HANAOutboundAdapter()
        a._client = MagicMock()
        a._client.connect = AsyncMock()
        a._client.disconnect = AsyncMock()
        a._client.health_check = AsyncMock(return_value=True)
        a._client.post = AsyncMock(return_value={"ConfirmationGroup": "SAP-CONF-001"})
        return a

    @pytest.mark.asyncio()
    async def test_report_completion(self, adapter):
        result = await adapter.report_completion(
            order_id="PO-001",
            qty_good=95,
            qty_reject=5,
            step_id="0010",
        )
        assert isinstance(result, ERPConfirmation)
        assert result.success is True
        assert result.erp_doc_number == "SAP-CONF-001"
        # Verify POST was called
        adapter._client.post.assert_awaited_once()
        payload = adapter._client.post.call_args.args[1]
        assert payload["OrderID"] == "PO-001"
        assert payload["ConfirmationYieldQuantity"] == "95"

    @pytest.mark.asyncio()
    async def test_report_consumption(self, adapter):
        adapter._client.post = AsyncMock(return_value={"MaterialDocument": "MAT-DOC-001"})
        result = await adapter.report_consumption(
            order_id="PO-001",
            materials=[
                MaterialConsumptionDTO(
                    material_code="RM-STEEL",
                    quantity=2.5,
                    uom="KG",
                ),
            ],
        )
        assert result.success is True
        assert result.erp_doc_number == "MAT-DOC-001"

    @pytest.mark.asyncio()
    async def test_report_scrap(self, adapter):
        result = await adapter.report_scrap(
            order_id="PO-001",
            qty_scrapped=3,
            reason_code="DEFECT",
        )
        assert result.success is True
        payload = adapter._client.post.call_args.args[1]
        assert payload["ConfirmationScrapQuantity"] == "3"
        assert payload["ConfirmationScrapReasonCode"] == "DEFECT"

    @pytest.mark.asyncio()
    async def test_report_labor(self, adapter):
        result = await adapter.report_labor(
            order_id="PO-001",
            operator_id="OP-001",
            duration_minutes=120.0,
        )
        assert result.success is True
        payload = adapter._client.post.call_args.args[1]
        assert payload["OpActualExecutionDuration"] == "120.0"
        assert payload["PersonnelNumber"] == "OP-001"

    @pytest.mark.asyncio()
    async def test_report_downtime(self, adapter):
        started = datetime(2026, 3, 15, 8, 0, 0, tzinfo=timezone.utc)
        result = await adapter.report_downtime(
            equipment_id="EQ-001",
            duration_minutes=30.0,
            reason_code="MAINT",
            started_at=started,
        )
        assert result.success is True
        payload = adapter._client.post.call_args.args[1]
        assert "Downtime: EQ-001 reason=MAINT" in payload["ConfirmationText"]

    @pytest.mark.asyncio()
    async def test_report_quality_result(self, adapter):
        adapter._client.post = AsyncMock(return_value={"InspectionLot": "IL-001"})
        result = await adapter.report_quality_result(
            order_id="PO-001",
            test_id="TEST-001",
            result="PASS",
            details={"measurement": 5.0},
        )
        assert result.success is True
        assert result.erp_doc_number == "IL-001"
