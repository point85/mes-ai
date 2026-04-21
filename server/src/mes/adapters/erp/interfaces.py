"""
ERP Adapter: Abstract interfaces for ERP inbound, outbound, and transform.

Concrete implementations are either vendor-specific plugins (SAP, Oracle, D365,
Infor) or the built-in MockERP adapter for development/testing.

Per ARCHITECTURE.md §9.2.4.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .dtos import (
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


class ERPInboundAdapter(ABC):
    """
    Pulls data from ERP into MES.

    Each method syncs a category of master/transactional data.
    The ``since`` parameter enables incremental sync (only changes after that timestamp).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the ERP system."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the ERP connection."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the adapter can communicate with the ERP system."""
        ...

    @abstractmethod
    async def sync_operations_requests(
        self, since: datetime | None = None,
    ) -> list[ProductionOrderDTO]:
        """Fetch new or changed production orders from ERP."""
        ...

    @abstractmethod
    async def sync_materials(
        self, since: datetime | None = None,
    ) -> list[MaterialDefinitionDTO]:
        """Fetch material master records from ERP."""
        ...

    @abstractmethod
    async def sync_products(
        self, since: datetime | None = None,
    ) -> list[ProductDefinitionDTO]:
        """Fetch product/item master records from ERP."""
        ...

    @abstractmethod
    async def sync_boms(
        self, product_id: str,
    ) -> list[BillOfMaterialDTO]:
        """Fetch BOMs for a given product from ERP."""
        ...

    @abstractmethod
    async def sync_routings(
        self, product_id: str,
    ) -> list[ProcessRouteDTO]:
        """Fetch process routes/routings for a given product from ERP."""
        ...

    @abstractmethod
    async def sync_work_cells(self) -> list[WorkCellDTO]:
        """Fetch work cell/resource definitions from ERP."""
        ...


class ERPOutboundAdapter(ABC):
    """
    Pushes data from MES back to ERP.

    Each method sends a specific report type. All return an ERPConfirmation
    indicating whether the ERP accepted the data.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the ERP system."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the ERP connection."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the adapter can communicate with the ERP system."""
        ...

    @abstractmethod
    async def report_completion(
        self,
        order_id: str,
        qty_good: int,
        qty_reject: int,
        step_id: str | None = None,
    ) -> ERPConfirmation:
        """Report production completion for an order."""
        ...

    @abstractmethod
    async def report_consumption(
        self,
        order_id: str,
        materials: list[MaterialConsumptionDTO],
    ) -> ERPConfirmation:
        """Report material consumption against an order."""
        ...

    @abstractmethod
    async def report_scrap(
        self,
        order_id: str,
        qty_scrapped: int,
        reason_code: str,
    ) -> ERPConfirmation:
        """Report scrapped quantity for an order."""
        ...

    @abstractmethod
    async def report_labor(
        self,
        order_id: str,
        operator_id: str,
        duration_minutes: float,
    ) -> ERPConfirmation:
        """Report labor time against an order."""
        ...

    @abstractmethod
    async def report_downtime(
        self,
        equipment_id: str,
        duration_minutes: float,
        reason_code: str,
        started_at: datetime,
    ) -> ERPConfirmation:
        """Report equipment downtime."""
        ...

    @abstractmethod
    async def report_quality_result(
        self,
        order_id: str,
        test_id: str,
        result: str,
        details: dict[str, Any],
    ) -> ERPConfirmation:
        """Report quality test result."""
        ...


class ERPTransformLayer:
    """
    Maps between MES internal models and ERP-specific data formats.

    Each ERP vendor adapter provides a concrete transform layer that knows
    how to translate vendor-specific field names, data types, and conventions
    into/from the MES canonical DTOs.

    The base implementation is a pass-through (mock/testing).
    """

    def to_production_order(self, erp_data: dict[str, Any]) -> ProductionOrderDTO:
        """Transform raw ERP data into a ProductionOrderDTO."""
        return ProductionOrderDTO(**erp_data)

    def from_completion(self, report: CompletionReport) -> dict[str, Any]:
        """Transform a CompletionReport into ERP-specific format."""
        return report.model_dump()

    def to_material(self, erp_data: dict[str, Any]) -> MaterialDefinitionDTO:
        """Transform raw ERP data into a MaterialDefinitionDTO."""
        return MaterialDefinitionDTO(**erp_data)

    def from_consumption(self, report: ConsumptionReport) -> dict[str, Any]:
        """Transform a ConsumptionReport into ERP-specific format."""
        return report.model_dump()
