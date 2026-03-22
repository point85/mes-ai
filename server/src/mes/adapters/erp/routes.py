"""
ERP Adapter: REST API routes for ERP integration.

Queue endpoints:
- GET    /api/v1/erp/queue          List failed queue items
- GET    /api/v1/erp/queue/stats    Queue statistics
- POST   /api/v1/erp/queue/{id}/retry   Retry a failed item

Inbound sync endpoints (ERP → MES):
- GET    /api/v1/erp/health         ERP adapter health status
- POST   /api/v1/erp/sync/production-orders   Sync production orders
- POST   /api/v1/erp/sync/materials           Sync materials
- POST   /api/v1/erp/sync/products            Sync products
- POST   /api/v1/erp/sync/boms               Sync BOMs for a product
- POST   /api/v1/erp/sync/routings            Sync routings for a product
- POST   /api/v1/erp/sync/work-centers        Sync work centers

Outbound report endpoints (MES → ERP):
- POST   /api/v1/erp/report/completion       Report production completion
- POST   /api/v1/erp/report/consumption      Report material consumption
- POST   /api/v1/erp/report/scrap            Report scrap
- POST   /api/v1/erp/report/labor            Report labor time
- POST   /api/v1/erp/report/downtime         Report equipment downtime
- POST   /api/v1/erp/report/quality-result   Report quality test result
- GET    /api/v1/erp/confirmations            List outbound confirmations (simulator)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import success_response, list_response
from mes.framework.db import get_db_session

from .dtos import MaterialConsumptionDTO
from .queue import ERPOutboundQueueService, QueueItemRead, QueueStats

router = APIRouter(
    prefix="/api/v1/erp",
    tags=["ERP Integration"],
)


# ── Request schemas for outbound reports ───────────────────────────────────

class CompletionRequest(BaseModel):
    order_id: str
    qty_good: int = Field(..., ge=0)
    qty_reject: int = Field(default=0, ge=0)
    step_id: str | None = None


class ConsumptionRequest(BaseModel):
    order_id: str
    materials: list[MaterialConsumptionDTO]


class ScrapRequest(BaseModel):
    order_id: str
    qty_scrapped: int = Field(..., gt=0)
    reason_code: str


class LaborRequest(BaseModel):
    order_id: str
    operator_id: str
    duration_minutes: float = Field(..., gt=0)


class DowntimeRequest(BaseModel):
    equipment_id: str
    duration_minutes: float = Field(..., gt=0)
    reason_code: str
    started_at: datetime


class QualityResultRequest(BaseModel):
    order_id: str
    test_id: str
    result: str
    details: dict[str, Any] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    product_id: str | None = None
    since: datetime | None = None


# ── Helper to get adapters from plugin manager ─────────────────────────────

def _get_erp_inbound():
    from mes.main import plugin_manager
    adapter = plugin_manager.get_adapter_by_type("erp_inbound")
    if adapter is None:
        from mes.framework.api.exceptions import MESException
        raise MESException(
            message="No ERP inbound adapter is running. Install and enable an ERP plugin.",
            status_code=503,
            error_code="ERP_ADAPTER_UNAVAILABLE",
        )
    return adapter


def _get_erp_outbound():
    from mes.main import plugin_manager
    adapter = plugin_manager.get_adapter_by_type("erp_outbound")
    if adapter is None:
        from mes.framework.api.exceptions import MESException
        raise MESException(
            message="No ERP outbound adapter is running. Install and enable an ERP plugin.",
            status_code=503,
            error_code="ERP_ADAPTER_UNAVAILABLE",
        )
    return adapter


@router.get("/queue", response_model=dict)
async def list_failed_items(
    db: AsyncSession = Depends(get_db_session),
):
    """List all failed ERP outbound queue items."""
    items = await ERPOutboundQueueService.list_failed(db)
    data = [
        QueueItemRead(
            id=str(item.id),
            report_type=item.report_type,
            payload=json.loads(item.payload),
            status=item.status,
            attempts=item.attempts,
            max_attempts=item.max_attempts,
            next_retry_at=item.next_retry_at,
            last_error=item.last_error,
            erp_doc_number=item.erp_doc_number,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ).model_dump()
        for item in items
    ]
    return success_response(data)


@router.get("/queue/stats", response_model=dict)
async def queue_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """Get ERP outbound queue statistics."""
    stats = await ERPOutboundQueueService.get_stats(db)
    return success_response(stats.model_dump())


@router.post("/queue/{item_id}/retry", response_model=dict)
async def retry_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Reset a failed queue item to pending for re-processing."""
    success = await ERPOutboundQueueService.retry_item(db, str(item_id))
    if not success:
        from mes.framework.api.exceptions import NotFoundException
        raise NotFoundException(resource="ERPOutboundQueueItem", resource_id=str(item_id))
    await db.commit()
    return success_response({"retried": True, "item_id": str(item_id)})


# ═══════════════════════════════════════════════════════════════════════════
# ERP Adapter Health
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/health", response_model=dict)
async def erp_health():
    """Check health of ERP inbound and outbound adapters."""
    from mes.main import plugin_manager

    ib_plugin = plugin_manager.get_adapter_plugin("erp_inbound")
    ob_plugin = plugin_manager.get_adapter_plugin("erp_outbound")

    result: dict[str, Any] = {
        "inbound": {
            "available": ib_plugin is not None,
            "plugin_id": ib_plugin.manifest.id if ib_plugin else None,
            "healthy": False,
        },
        "outbound": {
            "available": ob_plugin is not None,
            "plugin_id": ob_plugin.manifest.id if ob_plugin else None,
            "healthy": False,
        },
    }
    if ib_plugin and ib_plugin.instance:
        try:
            result["inbound"]["healthy"] = await ib_plugin.instance.health_check()
        except Exception:
            pass
    if ob_plugin and ob_plugin.instance:
        try:
            result["outbound"]["healthy"] = await ob_plugin.instance.health_check()
        except Exception:
            pass
    return success_response(result)


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Sync (ERP → MES)
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/sync/production-orders", response_model=dict)
async def sync_production_orders(
    since: datetime | None = Query(None, description="Only fetch orders changed after this timestamp"),
):
    """Pull production orders from the ERP adapter."""
    adapter = _get_erp_inbound()
    orders = await adapter.sync_production_orders(since=since)
    return list_response([o.model_dump(mode="json") for o in orders])


@router.post("/sync/materials", response_model=dict)
async def sync_materials(
    since: datetime | None = Query(None),
):
    """Pull material master records from the ERP adapter."""
    adapter = _get_erp_inbound()
    materials = await adapter.sync_materials(since=since)
    return list_response([m.model_dump(mode="json") for m in materials])


@router.post("/sync/products", response_model=dict)
async def sync_products(
    since: datetime | None = Query(None),
):
    """Pull product definitions from the ERP adapter."""
    adapter = _get_erp_inbound()
    products = await adapter.sync_products(since=since)
    return list_response([p.model_dump(mode="json") for p in products])


@router.post("/sync/boms", response_model=dict)
async def sync_boms(
    product_id: str = Query(..., description="Product code to fetch BOMs for"),
):
    """Pull bills of material for a specific product from the ERP adapter."""
    adapter = _get_erp_inbound()
    boms = await adapter.sync_boms(product_id)
    return list_response([b.model_dump(mode="json") for b in boms])


@router.post("/sync/routings", response_model=dict)
async def sync_routings(
    product_id: str = Query(..., description="Product code to fetch routings for"),
):
    """Pull process routings for a specific product from the ERP adapter."""
    adapter = _get_erp_inbound()
    routes = await adapter.sync_routings(product_id)
    return list_response([r.model_dump(mode="json") for r in routes])


@router.post("/sync/work-centers", response_model=dict)
async def sync_work_centers():
    """Pull work center definitions from the ERP adapter."""
    adapter = _get_erp_inbound()
    wcs = await adapter.sync_work_cells()
    return list_response([wc.model_dump(mode="json") for wc in wcs])


# ═══════════════════════════════════════════════════════════════════════════
# Outbound Reports (MES → ERP)
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/report/completion", response_model=dict)
async def report_completion(req: CompletionRequest):
    """Report production completion to the ERP adapter."""
    adapter = _get_erp_outbound()
    result = await adapter.report_completion(
        order_id=req.order_id,
        qty_good=req.qty_good,
        qty_reject=req.qty_reject,
        step_id=req.step_id,
    )
    return success_response(result.model_dump(mode="json"))


@router.post("/report/consumption", response_model=dict)
async def report_consumption(req: ConsumptionRequest):
    """Report material consumption to the ERP adapter."""
    adapter = _get_erp_outbound()
    result = await adapter.report_consumption(
        order_id=req.order_id,
        materials=req.materials,
    )
    return success_response(result.model_dump(mode="json"))


@router.post("/report/scrap", response_model=dict)
async def report_scrap(req: ScrapRequest):
    """Report scrap to the ERP adapter."""
    adapter = _get_erp_outbound()
    result = await adapter.report_scrap(
        order_id=req.order_id,
        qty_scrapped=req.qty_scrapped,
        reason_code=req.reason_code,
    )
    return success_response(result.model_dump(mode="json"))


@router.post("/report/labor", response_model=dict)
async def report_labor(req: LaborRequest):
    """Report labor time to the ERP adapter."""
    adapter = _get_erp_outbound()
    result = await adapter.report_labor(
        order_id=req.order_id,
        operator_id=req.operator_id,
        duration_minutes=req.duration_minutes,
    )
    return success_response(result.model_dump(mode="json"))


@router.post("/report/downtime", response_model=dict)
async def report_downtime(req: DowntimeRequest):
    """Report equipment downtime to the ERP adapter."""
    adapter = _get_erp_outbound()
    result = await adapter.report_downtime(
        equipment_id=req.equipment_id,
        duration_minutes=req.duration_minutes,
        reason_code=req.reason_code,
        started_at=req.started_at,
    )
    return success_response(result.model_dump(mode="json"))


@router.post("/report/quality-result", response_model=dict)
async def report_quality_result(req: QualityResultRequest):
    """Report quality test result to the ERP adapter."""
    adapter = _get_erp_outbound()
    result = await adapter.report_quality_result(
        order_id=req.order_id,
        test_id=req.test_id,
        result=req.result,
        details=req.details,
    )
    return success_response(result.model_dump(mode="json"))


@router.get("/confirmations", response_model=dict)
async def list_confirmations():
    """
    List outbound confirmations stored by the running ERP outbound adapter.

    This is primarily useful with the SAP ERP simulator, which stores all
    confirmations in memory for inspection.
    """
    adapter = _get_erp_outbound()
    confirmations = getattr(adapter, "confirmations", [])
    return list_response(confirmations)
