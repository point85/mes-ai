"""
MAT-MGMT: REST API routes for material management.

Endpoints:
- GET    /api/v1/materials                        List materials (optional type filter)
- POST   /api/v1/materials                        Create a material definition
- GET    /api/v1/materials/{material_id}           Get a material by ID
- PATCH  /api/v1/materials/{material_id}           Update a material
- DELETE /api/v1/materials/{material_id}           Soft-delete a material
- GET    /api/v1/material-lots                     List material lots
- POST   /api/v1/material-lots                     Create a material lot
- GET    /api/v1/material-lots/{lot_id}            Get a material lot by ID
- PATCH  /api/v1/material-lots/{lot_id}            Update a material lot
- POST   /api/v1/material-lots/{lot_id}/consume    Consume material from lot
- GET    /api/v1/units/{unit_id}/consumed-materials  Get consumed materials for a unit
- GET    /api/v1/lots/{lot_id}/consumed-materials   Get consumed materials for a WIP lot
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.pagination import PaginationParams, get_pagination_params
from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .schemas import (
    ConsumeRequest,
    ConsumptionRead,
    MaterialCreate,
    MaterialLotCreate,
    MaterialLotRead,
    MaterialLotUpdate,
    MaterialRead,
    MaterialUpdate,
)
from .service import MaterialLotService, MaterialService

router = APIRouter(prefix="/api/v1", tags=["Material Management"])
mat_svc = MaterialService
lot_svc = MaterialLotService


# ═══════════════════════════════════════════════════════════════════
# MaterialDefinition endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/materials")
async def list_materials(
    material_type: str | None = Query(None, description="Filter by type: raw, intermediate, finished"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.read")),
):
    """List active material definitions with optional type filter."""
    items, cursor, has_more = await mat_svc.list_materials(
        session, params, material_type=material_type,
    )
    return list_response(
        [MaterialRead.model_validate(m).model_dump() for m in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/materials/{material_id}")
async def get_material(
    material_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.read")),
):
    """Get a material definition by ID."""
    material = await mat_svc.get_material(session, material_id)
    return success_response(MaterialRead.model_validate(material).model_dump())


@router.post("/materials", status_code=201)
async def create_material(
    body: MaterialCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.create")),
):
    """Create a new material definition."""
    material = await mat_svc.create_material(session, **body.model_dump())
    await session.commit()
    return success_response(MaterialRead.model_validate(material).model_dump())


@router.patch("/materials/{material_id}")
async def update_material(
    material_id: UUID,
    body: MaterialUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.update")),
):
    """Update a material definition."""
    material = await mat_svc.update_material(
        session, material_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(MaterialRead.model_validate(material).model_dump())


@router.delete("/materials/{material_id}", status_code=204)
async def delete_material(
    material_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.delete")),
):
    """Soft-delete a material definition."""
    await mat_svc.delete_material(session, material_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# MaterialLot endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/material-lots")
async def list_material_lots(
    material_id: UUID | None = Query(None, description="Filter by material ID"),
    status: str | None = Query(None, description="Filter by status"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.read")),
):
    """List active material lots with optional filters."""
    items, cursor, has_more = await lot_svc.list_lots(
        session, params, material_id=material_id, status=status,
    )
    return list_response(
        [MaterialLotRead.model_validate(lot).model_dump() for lot in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/material-lots/{lot_id}")
async def get_material_lot(
    lot_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.read")),
):
    """Get a material lot by ID."""
    lot = await lot_svc.get_lot(session, lot_id)
    return success_response(MaterialLotRead.model_validate(lot).model_dump())


@router.post("/material-lots", status_code=201)
async def create_material_lot(
    body: MaterialLotCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.create")),
):
    """Create a new material lot (receive material into inventory)."""
    lot = await lot_svc.create_lot(session, **body.model_dump())
    await session.commit()
    return success_response(MaterialLotRead.model_validate(lot).model_dump())


@router.patch("/material-lots/{lot_id}")
async def update_material_lot(
    lot_id: UUID,
    body: MaterialLotUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.update")),
):
    """Update a material lot."""
    lot = await lot_svc.update_lot(
        session, lot_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(MaterialLotRead.model_validate(lot).model_dump())


# ─── Consumption ─────────────────────────────────────────────────


@router.post("/material-lots/{lot_id}/consume", status_code=201)
async def consume_material(
    lot_id: UUID,
    body: ConsumeRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.consume")),
):
    """Consume material from a lot against a WIP unit or lot."""
    consumption = await lot_svc.consume(
        session,
        lot_id,
        unit_id=body.unit_id,
        lot_wip_id=body.lot_id,
        step_id=body.step_id,
        quantity_consumed=body.quantity_consumed,
    )
    await session.commit()
    return success_response(ConsumptionRead.model_validate(consumption).model_dump())


@router.get("/units/{unit_id}/consumed-materials")
async def get_consumed_materials(
    unit_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.read")),
):
    """Get all materials consumed by a WIP unit (genealogy / traceability)."""
    items = await lot_svc.get_consumptions_for_unit(session, unit_id)
    return success_response(
        [ConsumptionRead.model_validate(c).model_dump() for c in items],
    )


@router.get("/lots/{lot_id}/consumed-materials")
async def get_lot_consumed_materials(
    lot_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("material.read")),
):
    """Get all materials consumed by a WIP lot (genealogy / traceability)."""
    items = await lot_svc.get_consumptions_for_lot(session, lot_id)
    return success_response(
        [ConsumptionRead.model_validate(c).model_dump() for c in items],
    )
