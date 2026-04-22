"""
Oracle Cloud ERP: Concrete ERP adapter implementations.

OracleInboundAdapter — pulls work orders, items, products,
  structures (BOMs), routings, and work centers from Oracle via REST APIs.

OracleOutboundAdapter — pushes completions, material transactions,
  scrap reports, labor postings, and quality results to Oracle.
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
    OperationsRequestDTO,
    WorkCellDTO,
)
from mes.adapters.erp.interfaces import ERPInboundAdapter, ERPOutboundAdapter

from .client import OracleClient
from .config import oracle_settings
from .transform import OracleTransformLayer

logger = logging.getLogger("mes.adapters.erp.oracle.adapter")


class OracleInboundAdapter(ERPInboundAdapter):
    """
    Pulls master and transactional data from Oracle Cloud ERP into MES.

    Uses Oracle Fusion REST APIs for:
      - Work orders
      - Inventory items (materials)
      - Finished goods (products)
      - Item structures (BOMs)
      - Routings / operations
      - Work centers
    """

    def __init__(self) -> None:
        self._client = OracleClient()
        self._transform = OracleTransformLayer()

    async def connect(self) -> None:
        await self._client.connect()
        logger.info("Oracle Cloud ERP inbound adapter connected")

    async def disconnect(self) -> None:
        await self._client.disconnect()
        logger.info("Oracle Cloud ERP inbound adapter disconnected")

    async def health_check(self) -> bool:
        return await self._client.health_check()

    async def sync_operations_requests(
        self, since: datetime | None = None,
    ) -> list[OperationsRequestDTO]:
        """Fetch work orders, optionally filtered by last-updated date."""
        filters = [
            f"OrganizationCode='{oracle_settings.ORACLE_ORGANIZATION_CODE}'",
        ]
        if since:
            filters.append(f"LastUpdateDate>{since.isoformat()}")

        raw_orders = await self._client.get_list(
            oracle_settings.ORACLE_WORK_ORDER_PATH,
            q_filter=";".join(filters),
        )
        return [self._transform.to_operations_request(o) for o in raw_orders]

    async def sync_materials(
        self, since: datetime | None = None,
    ) -> list[MaterialDefinitionDTO]:
        """Fetch inventory item records filtered by organization."""
        filters = [
            f"OrganizationCode='{oracle_settings.ORACLE_ORGANIZATION_CODE}'",
        ]
        if since:
            filters.append(f"LastUpdateDate>{since.isoformat()}")

        raw_materials = await self._client.get_list(
            oracle_settings.ORACLE_ITEM_PATH,
            q_filter=";".join(filters),
        )
        return [self._transform.to_material(m) for m in raw_materials]

    async def sync_products(
        self, since: datetime | None = None,
    ) -> list[ProductDefinitionDTO]:
        """Fetch finished-good item definitions from Oracle."""
        filters = [
            f"OrganizationCode='{oracle_settings.ORACLE_ORGANIZATION_CODE}'",
            "ItemType='FINISHED_GOOD'",
        ]
        if since:
            filters.append(f"LastUpdateDate>{since.isoformat()}")

        raw_products = await self._client.get_list(
            oracle_settings.ORACLE_ITEM_PATH,
            q_filter=";".join(filters),
        )
        return [self._transform.to_product(p) for p in raw_products]

    async def sync_boms(self, product_id: str) -> list[BillOfMaterialDTO]:
        """Fetch item structures (BOMs) for a given product with expanded components."""
        filters = [
            f"ItemNumber='{product_id}'",
            f"OrganizationCode='{oracle_settings.ORACLE_ORGANIZATION_CODE}'",
        ]
        raw_boms = await self._client.get_list(
            oracle_settings.ORACLE_STRUCTURE_PATH,
            q_filter=";".join(filters),
            params={"expand": "Component"},
        )
        return [self._transform.to_bom(b) for b in raw_boms]

    async def sync_routings(self, product_id: str) -> list[ProcessRouteDTO]:
        """Fetch routings/operations for a given product."""
        filters = [
            f"ItemNumber='{product_id}'",
        ]
        raw_routings = await self._client.get_list(
            oracle_settings.ORACLE_ROUTING_PATH,
            q_filter=";".join(filters),
            params={"expand": "Operation"},
        )
        return [self._transform.to_routing(r) for r in raw_routings]

    async def sync_work_cells(self) -> list[WorkCellDTO]:
        """Fetch work center definitions for the configured organization."""
        filters = [
            f"OrganizationCode='{oracle_settings.ORACLE_ORGANIZATION_CODE}'",
        ]
        raw_wcs = await self._client.get_list(
            oracle_settings.ORACLE_WORK_CENTER_PATH,
            q_filter=";".join(filters),
        )
        return [self._transform.to_work_cell(wc) for wc in raw_wcs]


class OracleOutboundAdapter(ERPOutboundAdapter):
    """
    Pushes MES data back to Oracle Cloud ERP.

    Uses Oracle Fusion REST APIs for:
      - Work order completions
      - Inventory transactions (material consumption)
      - Scrap reporting
      - Labor/resource reporting
      - Downtime reporting
      - Quality results
    """

    def __init__(self) -> None:
        self._client = OracleClient()
        self._transform = OracleTransformLayer()

    async def connect(self) -> None:
        await self._client.connect()
        logger.info("Oracle Cloud ERP outbound adapter connected")

    async def disconnect(self) -> None:
        await self._client.disconnect()
        logger.info("Oracle Cloud ERP outbound adapter disconnected")

    async def health_check(self) -> bool:
        return await self._client.health_check()

    async def report_completion(
        self,
        order_id: str,
        qty_good: int,
        qty_reject: int,
        step_id: str | None = None,
    ) -> ERPConfirmation:
        """Post a work order completion to Oracle."""
        from mes.adapters.erp.dtos import CompletionReport

        report = CompletionReport(
            erp_reference=order_id,
            qty_good=qty_good,
            qty_reject=qty_reject,
            step_id=step_id,
        )
        payload = self._transform.from_completion(report)
        payload["OrganizationCode"] = oracle_settings.ORACLE_ORGANIZATION_CODE

        result = await self._client.post(
            oracle_settings.ORACLE_COMPLETION_PATH,
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=str(result.get("CompletionTransactionId", "")),
            message="Oracle completion posted",
            metadata={"oracle_response": result},
        )

    async def report_consumption(
        self,
        order_id: str,
        materials: list[MaterialConsumptionDTO],
    ) -> ERPConfirmation:
        """Post a material issue transaction to Oracle."""
        from mes.adapters.erp.dtos import ConsumptionReport

        report = ConsumptionReport(
            erp_reference=order_id,
            materials=materials,
        )
        payload = self._transform.from_consumption(report)
        payload["OrganizationCode"] = oracle_settings.ORACLE_ORGANIZATION_CODE

        result = await self._client.post(
            oracle_settings.ORACLE_TRANSACTION_PATH,
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=str(result.get("TransactionHeaderId", "")),
            message="Oracle material transaction posted",
            metadata={"oracle_response": result},
        )

    async def report_scrap(
        self,
        order_id: str,
        qty_scrapped: int,
        reason_code: str,
    ) -> ERPConfirmation:
        """Post a scrap transaction to Oracle."""
        payload = {
            "WorkOrderNumber": order_id,
            "OperationSequenceNumber": "10",
            "CompletedQuantity": 0,
            "RejectedQuantity": qty_scrapped,
            "ScrapReasonCode": reason_code,
            "TransactionType": "WIP_SCRAP",
            "OrganizationCode": oracle_settings.ORACLE_ORGANIZATION_CODE,
        }
        result = await self._client.post(
            oracle_settings.ORACLE_COMPLETION_PATH,
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=str(result.get("CompletionTransactionId", "")),
            message="Oracle scrap transaction posted",
            metadata={"oracle_response": result},
        )

    async def report_labor(
        self,
        order_id: str,
        operator_id: str,
        duration_minutes: float,
    ) -> ERPConfirmation:
        """Post a labor/resource transaction to Oracle."""
        payload = {
            "WorkOrderNumber": order_id,
            "OperationSequenceNumber": "10",
            "ResourceCode": operator_id,
            "ResourceUsage": duration_minutes,
            "ResourceUOMCode": "MIN",
            "TransactionType": "RESOURCE",
            "OrganizationCode": oracle_settings.ORACLE_ORGANIZATION_CODE,
        }
        result = await self._client.post(
            oracle_settings.ORACLE_TRANSACTION_PATH,
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=str(result.get("TransactionHeaderId", "")),
            message="Oracle labor transaction posted",
            metadata={"oracle_response": result},
        )

    async def report_downtime(
        self,
        equipment_id: str,
        duration_minutes: float,
        reason_code: str,
        started_at: datetime,
    ) -> ERPConfirmation:
        """
        Post equipment downtime to Oracle.

        Oracle doesn't have a direct downtime API — this maps to
        a resource transaction with a downtime reason code.
        """
        payload = {
            "WorkOrderNumber": "",  # Requires order context from caller
            "OperationSequenceNumber": "10",
            "ResourceCode": equipment_id,
            "ResourceUsage": duration_minutes,
            "ResourceUOMCode": "MIN",
            "ReasonCode": reason_code,
            "TransactionType": "RESOURCE",
            "TransactionDate": started_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "OrganizationCode": oracle_settings.ORACLE_ORGANIZATION_CODE,
        }
        result = await self._client.post(
            oracle_settings.ORACLE_TRANSACTION_PATH,
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=str(result.get("TransactionHeaderId", "")),
            message="Oracle downtime transaction posted",
            metadata={"oracle_response": result},
        )

    async def report_quality_result(
        self,
        order_id: str,
        test_id: str,
        result: str,
        details: dict[str, Any],
    ) -> ERPConfirmation:
        """Post a quality inspection result to Oracle."""
        payload = {
            "WorkOrderNumber": order_id,
            "InspectionId": test_id,
            "Result": result,
            "ResultDetails": str(details),
            "OrganizationCode": oracle_settings.ORACLE_ORGANIZATION_CODE,
        }
        result_data = await self._client.post(
            oracle_settings.ORACLE_QUALITY_PATH,
            payload,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=str(result_data.get("QualityResultId", "")),
            message="Oracle quality result posted",
            metadata={"oracle_response": result_data},
        )
