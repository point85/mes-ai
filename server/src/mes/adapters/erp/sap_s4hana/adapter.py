"""
SAP S/4HANA: Concrete ERP adapter implementations.

SAPS4HANAInboundAdapter — pulls production orders, materials, products,
  BOMs, routings, and work centers from SAP via OData V4 APIs.

SAPS4HANAOutboundAdapter — pushes production confirmations, goods
  movements, scrap reports, labor postings, and quality results to SAP.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

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
from mes.adapters.erp.interfaces import ERPInboundAdapter, ERPOutboundAdapter

from .client import SAPS4HANAClient
from .config import sap_settings
from .transform import SAPS4HANATransformLayer

logger = logging.getLogger("mes.adapters.erp.sap_s4hana.adapter")


class SAPS4HANAInboundAdapter(ERPInboundAdapter):
    """
    Pulls master and transactional data from SAP S/4HANA into MES.

    Uses OData V4 APIs for:
      - Production orders (Manufacturing Order)
      - Materials (Material Master)
      - Products (finished goods)
      - BOMs (Bill of Material)
      - Routings (Production Routing)
      - Work Centers
    """

    def __init__(self) -> None:
        self._client = SAPS4HANAClient()
        self._transform = SAPS4HANATransformLayer()

    async def connect(self) -> None:
        await self._client.connect()
        logger.info("SAP S/4HANA inbound adapter connected")

    async def disconnect(self) -> None:
        await self._client.disconnect()
        logger.info("SAP S/4HANA inbound adapter disconnected")

    async def health_check(self) -> bool:
        return await self._client.health_check()

    async def sync_production_orders(
        self, since: datetime | None = None,
    ) -> list[ProductionOrderDTO]:
        """Fetch production orders, optionally filtered by last-changed date."""
        filter_expr = None
        if since:
            filter_expr = f"LastChangeDateTime gt {since.isoformat()}"

        # Filter by plant
        plant_filter = f"ProductionPlant eq '{sap_settings.SAP_PLANT}'"
        if filter_expr:
            filter_expr = f"{filter_expr} and {plant_filter}"
        else:
            filter_expr = plant_filter

        raw_orders = await self._client.get_list(
            sap_settings.SAP_PRODUCTION_ORDER_PATH + "/ProductionOrder",
            filter_expr=filter_expr,
        )
        return [self._transform.to_production_order(o) for o in raw_orders]

    async def sync_materials(
        self, since: datetime | None = None,
    ) -> list[MaterialDefinitionDTO]:
        """Fetch material master records filtered by plant."""
        filter_expr = f"Plant eq '{sap_settings.SAP_PLANT}'"
        if since:
            filter_expr += f" and LastChangeDateTime gt {since.isoformat()}"

        raw_materials = await self._client.get_list(
            sap_settings.SAP_MATERIAL_PATH + "/A_Material",
            filter_expr=filter_expr,
        )
        return [self._transform.to_material(m) for m in raw_materials]

    async def sync_products(
        self, since: datetime | None = None,
    ) -> list[ProductDefinitionDTO]:
        """Fetch finished product definitions from SAP."""
        # FERT = finished product in SAP material types
        filter_expr = f"MaterialType eq 'FERT' and Plant eq '{sap_settings.SAP_PLANT}'"
        if since:
            filter_expr += f" and LastChangeDateTime gt {since.isoformat()}"

        raw_products = await self._client.get_list(
            sap_settings.SAP_PRODUCT_PATH + "/A_Product",
            filter_expr=filter_expr,
        )
        return [self._transform.to_product(p) for p in raw_products]

    async def sync_boms(self, product_id: str) -> list[BillOfMaterialDTO]:
        """Fetch BOMs for a given product with expanded items."""
        filter_expr = (
            f"Material eq '{product_id}' "
            f"and Plant eq '{sap_settings.SAP_PLANT}'"
        )
        raw_boms = await self._client.get_list(
            sap_settings.SAP_BOM_PATH + "/A_BillOfMaterial",
            filter_expr=filter_expr,
            params={"$expand": "to_BOMItem"},
        )
        return [self._transform.to_bom(b) for b in raw_boms]

    async def sync_routings(self, product_id: str) -> list[ProcessRouteDTO]:
        """Fetch production routings for a given product with expanded operations."""
        filter_expr = f"Material eq '{product_id}'"
        raw_routings = await self._client.get_list(
            sap_settings.SAP_ROUTING_PATH + "/A_ProductionRouting",
            filter_expr=filter_expr,
            params={"$expand": "to_Operation"},
        )
        return [self._transform.to_routing(r) for r in raw_routings]

    async def sync_work_cells(self) -> list[WorkCellDTO]:
        """Fetch work center definitions for the configured plant."""
        filter_expr = f"Plant eq '{sap_settings.SAP_PLANT}'"
        raw_wcs = await self._client.get_list(
            sap_settings.SAP_WORK_CENTER_PATH + "/A_WorkCenter",
            filter_expr=filter_expr,
        )
        return [self._transform.to_work_cell(wc) for wc in raw_wcs]


class SAPS4HANAOutboundAdapter(ERPOutboundAdapter):
    """
    Pushes MES data back to SAP S/4HANA.

    Uses Production Order Confirmation API for completions/scrap/labor,
    and Goods Movement for material consumption.
    """

    def __init__(self) -> None:
        self._client = SAPS4HANAClient()
        self._transform = SAPS4HANATransformLayer()

    async def connect(self) -> None:
        await self._client.connect()
        logger.info("SAP S/4HANA outbound adapter connected")

    async def disconnect(self) -> None:
        await self._client.disconnect()
        logger.info("SAP S/4HANA outbound adapter disconnected")

    async def health_check(self) -> bool:
        return await self._client.health_check()

    async def report_completion(
        self,
        order_id: str,
        qty_good: int,
        qty_reject: int,
        step_id: str | None = None,
    ) -> ERPConfirmation:
        """Post a production order confirmation to SAP."""
        from mes.adapters.erp.dtos import CompletionReport

        report = CompletionReport(
            erp_reference=order_id,
            qty_good=qty_good,
            qty_reject=qty_reject,
            step_id=step_id,
        )
        payload = self._transform.from_completion(report)

        result = await self._client.post(
            sap_settings.SAP_CONFIRMATION_PATH + "/ProdnOrdConf2",
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=result.get("ConfirmationGroup", ""),
            message="SAP confirmation posted",
            metadata={"sap_response": result},
        )

    async def report_consumption(
        self,
        order_id: str,
        materials: list[MaterialConsumptionDTO],
    ) -> ERPConfirmation:
        """Post a goods issue (261 movement type) to SAP."""
        from mes.adapters.erp.dtos import ConsumptionReport

        report = ConsumptionReport(
            erp_reference=order_id,
            materials=materials,
        )
        payload = self._transform.from_consumption(report)

        result = await self._client.post(
            sap_settings.SAP_PRODUCTION_ORDER_PATH + "/GoodsMovement",
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=result.get("MaterialDocument", ""),
            message="SAP goods movement posted",
            metadata={"sap_response": result},
        )

    async def report_scrap(
        self,
        order_id: str,
        qty_scrapped: int,
        reason_code: str,
    ) -> ERPConfirmation:
        """Post a scrap confirmation to SAP (confirmation with scrap qty only)."""
        payload = {
            "OrderID": order_id,
            "OrderOperation": "0010",
            "ConfirmationYieldQuantity": "0",
            "ConfirmationScrapQuantity": str(qty_scrapped),
            "ConfirmationScrapReasonCode": reason_code,
            "IsFinalConfirmation": False,
        }
        result = await self._client.post(
            sap_settings.SAP_CONFIRMATION_PATH + "/ProdnOrdConf2",
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=result.get("ConfirmationGroup", ""),
            message="SAP scrap confirmation posted",
            metadata={"sap_response": result},
        )

    async def report_labor(
        self,
        order_id: str,
        operator_id: str,
        duration_minutes: float,
    ) -> ERPConfirmation:
        """Post labor/activity confirmation to SAP."""
        payload = {
            "OrderID": order_id,
            "OrderOperation": "0010",
            "ConfirmationYieldQuantity": "0",
            "ConfirmationScrapQuantity": "0",
            "OpActualExecutionDuration": str(duration_minutes),
            "OpExecDurationUnit": "MIN",
            "PersonnelNumber": operator_id,
            "IsFinalConfirmation": False,
        }
        result = await self._client.post(
            sap_settings.SAP_CONFIRMATION_PATH + "/ProdnOrdConf2",
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=result.get("ConfirmationGroup", ""),
            message="SAP labor confirmation posted",
            metadata={"sap_response": result},
        )

    async def report_downtime(
        self,
        equipment_id: str,
        duration_minutes: float,
        reason_code: str,
        started_at: datetime,
    ) -> ERPConfirmation:
        """
        Post equipment downtime to SAP.

        SAP doesn't have a direct downtime API — this maps to a
        production confirmation with zero yield and a reason code.
        """
        payload = {
            "OrderID": "",  # Requires order context from caller
            "OrderOperation": "0010",
            "ConfirmationYieldQuantity": "0",
            "ConfirmationScrapQuantity": "0",
            "OpActualExecutionDuration": str(duration_minutes),
            "OpExecDurationUnit": "MIN",
            "ConfirmationText": f"Downtime: {equipment_id} reason={reason_code}",
            "PostingDate": started_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "IsFinalConfirmation": False,
        }
        result = await self._client.post(
            sap_settings.SAP_CONFIRMATION_PATH + "/ProdnOrdConf2",
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=result.get("ConfirmationGroup", ""),
            message="SAP downtime confirmation posted",
            metadata={"sap_response": result},
        )

    async def report_quality_result(
        self,
        order_id: str,
        test_id: str,
        result: str,
        details: dict[str, Any],
    ) -> ERPConfirmation:
        """
        Post a quality result to SAP.

        Maps to SAP QM inspection lot result recording.
        """
        payload = {
            "InspectionLot": order_id,
            "InspectionOperation": test_id,
            "InspectionResult": result,
            "InspectionResultText": str(details),
        }
        result_data = await self._client.post(
            sap_settings.SAP_CONFIRMATION_PATH + "/QualityResult",
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=result_data.get("InspectionLot", ""),
            message="SAP quality result posted",
            metadata={"sap_response": result_data},
        )
