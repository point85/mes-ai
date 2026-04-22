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

Simulator CRUD endpoints (for editing in-memory ERP data):
- POST   /api/v1/erp/simulator/materials          Create a material
- PUT    /api/v1/erp/simulator/materials/{code}    Update a material
- DELETE /api/v1/erp/simulator/materials/{code}    Delete a material
- GET    /api/v1/erp/simulator/options             Dropdown options (material types, UOMs, ERP type)
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
        from mes.framework.api.exceptions import ServiceUnavailableException
        raise ServiceUnavailableException(
            message="No ERP inbound adapter is running. Install and enable an ERP plugin.",
            details={"error_code": "ERP_ADAPTER_UNAVAILABLE"},
        )
    return adapter


def _get_erp_outbound():
    from mes.main import plugin_manager
    adapter = plugin_manager.get_adapter_by_type("erp_outbound")
    if adapter is None:
        from mes.framework.api.exceptions import ServiceUnavailableException
        raise ServiceUnavailableException(
            message="No ERP outbound adapter is running. Install and enable an ERP plugin.",
            details={"error_code": "ERP_ADAPTER_UNAVAILABLE"},
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


@router.post("/sync/operations-requests", response_model=dict)
async def sync_operations_requests(
    since: datetime | None = Query(None, description="Only fetch orders changed after this timestamp"),
    enqueue: bool = Query(True, description="Persist orders to the inbound queue for processing"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Pull production orders from the ERP adapter.

    When ``enqueue=True`` (default) the orders are also persisted to the
    ``erp_inbound_orders`` queue for asynchronous processing by the
    registered ``OrderProcessor``.
    """
    adapter = _get_erp_inbound()
    orders = await adapter.sync_operations_requests(since=since)

    enqueued_ids: list[str] = []
    if enqueue and orders:
        from .inbound_queue import ERPInboundQueueService
        enqueued_ids = await ERPInboundQueueService.enqueue_from_sync(session, orders)
        await session.commit()

    data = [o.model_dump(mode="json") for o in orders]
    return success_response({
        "orders": data,
        "total": len(data),
        "enqueued": len(enqueued_ids),
    })


@router.post("/sync/materials", response_model=dict)
async def sync_materials(
    since: datetime | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Pull material master records from the ERP adapter and persist to DB."""
    from sqlalchemy import select
    from mes.core.material.models import MaterialDefinition
    from mes.core.material.service import MaterialService

    adapter = _get_erp_inbound()
    materials = await adapter.sync_materials(since=since)

    # Upsert each material into the MES database
    for dto in materials:
        result = await session.execute(
            select(MaterialDefinition).where(MaterialDefinition.code == dto.code)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            await MaterialService.create_material(
                session,
                code=dto.code,
                name=dto.name,
                material_type=dto.material_type,
                uom=dto.uom,
                revision=dto.revision,
                description=dto.description,
                shelf_life_days=dto.shelf_life_days,
            )
        else:
            if not existing.is_active:
                existing.is_active = True
            existing.name = dto.name
            existing.material_type = dto.material_type
            existing.uom = dto.uom
            existing.revision = dto.revision
            existing.description = dto.description
            existing.shelf_life_days = dto.shelf_life_days
            await session.flush()
    await session.commit()

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
    db: AsyncSession = Depends(get_db_session),
):
    """Pull process routings for a specific product from the ERP adapter and persist to the MES database."""
    adapter = _get_erp_inbound()
    routes = await adapter.sync_routings(product_id)

    # Persist ERP routes → MES OperationsDefinition + ProcessSegment tables
    from mes.core.product_def.service import ProductDefService
    await ProductDefService.sync_routes_from_erp(db, routes)
    await db.commit()

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

    This is useful with ERP simulator plugins (SAP or Oracle), which store
    all confirmations in memory for inspection.
    """
    adapter = _get_erp_outbound()
    confirmations = getattr(adapter, "confirmations", [])
    return list_response(confirmations)


# ═══════════════════════════════════════════════════════════════════════════
# Simulator CRUD — edit in-memory ERP data via the GUI
# ═══════════════════════════════════════════════════════════════════════════

# UOM symbols available in the simulator (shared across all ERP types)
_SIMULATOR_UOM_OPTIONS = [
    {"symbol": "EA",  "name": "Each"},
    {"symbol": "KG",  "name": "Kilogram"},
    {"symbol": "G",   "name": "Gram"},
    {"symbol": "L",   "name": "Liter"},
    {"symbol": "M",   "name": "Meter"},
    {"symbol": "KM",  "name": "Kilometer"},
    {"symbol": "PC",  "name": "Piece"},
    {"symbol": "M2",  "name": "Square Meter"},
    {"symbol": "M3",  "name": "Cubic Meter"},
]


class MaterialCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=120)
    material_type: str = Field(..., min_length=1)
    uom: str = Field(..., min_length=1)
    revision: str | None = None
    description: str = Field(default="")
    shelf_life_days: int | None = None


class MaterialUpdateRequest(BaseModel):
    name: str | None = None
    material_type: str | None = None
    uom: str | None = None
    revision: str | None = None
    description: str | None = None
    shelf_life_days: int | None = Field(default=None)


@router.get("/simulator/options", response_model=dict)
async def simulator_options():
    """Return dropdown options for material types and UOMs, plus ERP type."""
    adapter = _get_erp_inbound()
    erp_type = getattr(adapter, "erp_type", "unknown")
    if hasattr(adapter, "material_type_options"):
        material_types = adapter.material_type_options()
    else:
        material_types = []
    return success_response({
        "erp_type": erp_type,
        "material_types": material_types,
        "uom_options": _SIMULATOR_UOM_OPTIONS,
    })


@router.post("/simulator/materials", response_model=dict)
async def create_simulator_material(
    req: MaterialCreateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new material in the simulator's in-memory store and persist to DB."""
    from mes.core.material.service import MaterialService

    adapter = _get_erp_inbound()
    if not hasattr(adapter, "get_material"):
        from mes.framework.api.exceptions import MESException
        raise MESException(
            message="Running ERP adapter does not support simulator CRUD",
            status_code=400,
            error_code="NOT_A_SIMULATOR",
        )
    if adapter.get_material(req.code) is not None:
        from mes.framework.api.exceptions import MESException
        raise MESException(
            message=f"Material '{req.code}' already exists",
            status_code=409,
            error_code="DUPLICATE_MATERIAL",
        )
    erp_record = adapter.build_material_record(
        code=req.code,
        name=req.name,
        material_type=req.material_type,
        uom=req.uom,
        revision=req.revision,
        description=req.description,
        shelf_life_days=req.shelf_life_days,
    )
    adapter.add_material(erp_record)
    dto = adapter._transform.to_material(erp_record)

    # Persist to MES database
    await MaterialService.create_material(
        session,
        code=dto.code,
        name=dto.name,
        material_type=dto.material_type,
        uom=dto.uom,
        revision=dto.revision,
        description=dto.description,
        shelf_life_days=dto.shelf_life_days,
    )
    await session.commit()

    return success_response(dto.model_dump(mode="json"))


@router.put("/simulator/materials/{code}", response_model=dict)
async def update_simulator_material(
    code: str,
    req: MaterialUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Update an existing material in the simulator's in-memory store and DB."""
    from sqlalchemy import select
    from mes.core.material.models import MaterialDefinition
    from mes.core.material.service import MaterialService

    adapter = _get_erp_inbound()
    if not hasattr(adapter, "update_material"):
        from mes.framework.api.exceptions import MESException
        raise MESException(
            message="Running ERP adapter does not support simulator CRUD",
            status_code=400,
            error_code="NOT_A_SIMULATOR",
        )
    existing = adapter.get_material(code)
    if existing is None:
        from mes.framework.api.exceptions import NotFoundException
        raise NotFoundException(resource="Material", resource_id=code)
    updates = adapter.build_material_updates(
        name=req.name,
        material_type=req.material_type,
        uom=req.uom,
        revision=req.revision,
        description=req.description,
        shelf_life_days=req.shelf_life_days,
    )
    updated = adapter.update_material(code, updates)
    dto = adapter._transform.to_material(updated)

    # Persist to MES database
    result = await session.execute(
        select(MaterialDefinition).where(
            MaterialDefinition.code == code,
            MaterialDefinition.is_active.is_(True),
        )
    )
    db_material = result.scalar_one_or_none()
    if db_material is not None:
        db_updates: dict[str, Any] = {}
        if req.name is not None:
            db_updates["name"] = req.name
        if req.material_type is not None:
            db_updates["material_type"] = dto.material_type
        if req.uom is not None:
            db_updates["uom"] = req.uom
        if req.revision is not None:
            db_updates["revision"] = req.revision
        if req.description is not None:
            db_updates["description"] = req.description
        if req.shelf_life_days is not None:
            db_updates["shelf_life_days"] = req.shelf_life_days
        await MaterialService.update_material(session, db_material.id, **db_updates)
        await session.commit()

    return success_response(dto.model_dump(mode="json"))


@router.delete("/simulator/materials/{code}", response_model=dict)
async def delete_simulator_material(
    code: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a material from the simulator's in-memory store and soft-delete from DB."""
    from sqlalchemy import select
    from mes.core.material.models import MaterialDefinition
    from mes.core.material.service import MaterialService

    adapter = _get_erp_inbound()
    if not hasattr(adapter, "delete_material"):
        from mes.framework.api.exceptions import MESException
        raise MESException(
            message="Running ERP adapter does not support simulator CRUD",
            status_code=400,
            error_code="NOT_A_SIMULATOR",
        )
    # Remove from simulator in-memory store (best-effort)
    adapter.delete_material(code)

    # Soft-delete from MES database
    result = await session.execute(
        select(MaterialDefinition).where(
            MaterialDefinition.code == code,
            MaterialDefinition.is_active.is_(True),
        )
    )
    db_material = result.scalar_one_or_none()
    if db_material is not None:
        await MaterialService.delete_material(session, db_material.id)
        await session.commit()
        return success_response({"deleted": True, "code": code})

    from mes.framework.api.exceptions import NotFoundException
    raise NotFoundException(resource="Material", resource_id=code)


# ═══════════════════════════════════════════════════════════════════════════
# Inbound Order Queue  (ERP → MES processing pipeline)
# ═══════════════════════════════════════════════════════════════════════════


class InboundOrderPayload(BaseModel):
    """Payload for directly enqueuing an ERP order."""
    erp_reference: str = Field(..., description="Unique ERP order reference")
    product_code: str = Field(..., description="Product code in MES")
    quantity_ordered: int = Field(..., ge=1)
    priority: int = Field(default=0)
    planned_start: str | None = None
    planned_end: str | None = None
    uom: str | None = None
    metadata: dict[str, Any] | None = None


class InboundOrderBatch(BaseModel):
    orders: list[InboundOrderPayload]


@router.post("/inbound/queue", response_model=dict)
async def enqueue_inbound_orders(
    body: InboundOrderBatch,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Directly enqueue ERP orders for processing (push model).

    Use this when the ERP system pushes orders to MES via HTTP
    rather than having MES pull them from the ERP adapter.
    Duplicate ``erp_reference`` values in pending/retry status are skipped.
    """
    from .inbound_queue import ERPInboundQueueService
    payloads = [o.model_dump(mode="json") for o in body.orders]
    ids = await ERPInboundQueueService.enqueue_from_sync(db, payloads)
    await db.commit()
    return success_response({"enqueued": len(ids), "total": len(body.orders)})


@router.get("/inbound/queue", response_model=dict)
async def list_inbound_items(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    """List inbound order queue items."""
    from .inbound_queue import ERPInboundQueueService, InboundOrderRead
    items = await ERPInboundQueueService.list_items(db, status=status, limit=limit)
    data = [
        InboundOrderRead(
            id=str(item.id),
            erp_reference=item.erp_reference,
            product_code=item.product_code,
            payload=json.loads(item.payload),
            status=item.status,
            order_id=item.order_id,
            wip_ids=json.loads(item.wip_ids) if item.wip_ids else None,
            processor_name=item.processor_name,
            attempts=item.attempts,
            max_attempts=item.max_attempts,
            next_retry_at=item.next_retry_at,
            last_error=item.last_error,
            processed_at=item.processed_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ).model_dump(mode="json")
        for item in items
    ]
    return list_response(data)


@router.get("/inbound/queue/stats", response_model=dict)
async def inbound_queue_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """Get inbound order queue statistics."""
    from .inbound_queue import ERPInboundQueueService
    stats = await ERPInboundQueueService.get_stats(db)
    return success_response(stats.model_dump())


@router.post("/inbound/queue/process", response_model=dict)
async def process_inbound_queue(
    batch_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Manually trigger processing of pending inbound orders.

    Normally this runs automatically every 5 seconds.  This endpoint
    lets you trigger it on demand (e.g. after seeding demo data).
    """
    from .inbound_queue import ERPInboundQueueService
    processed = await ERPInboundQueueService.process_queue(db, batch_size=batch_size)
    await db.commit()
    return success_response({"processed": processed})


@router.post("/inbound/queue/{item_id}/retry", response_model=dict)
async def retry_inbound_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Reset a failed inbound order to pending for reprocessing."""
    from .inbound_queue import ERPInboundQueueService
    await ERPInboundQueueService.retry_item(db, str(item_id))
    await db.commit()
    return success_response({"retried": True, "item_id": str(item_id)})
