"""
PHYS-MODEL: REST API routes for the physical asset hierarchy.

Endpoints per ARCHITECTURE.md §6.3 — Physical Model (PHYS-MODEL):
- Sites CRUD:              /api/v1/sites
- Areas within a site:     /api/v1/sites/{site_id}/areas
- Lines within an area:    /api/v1/areas/{area_id}/lines
- Work cells in a line:    /api/v1/lines/{line_id}/work-cells
- Equipment in a WC:       /api/v1/work-cells/{wc_id}/equipment
- Equipment status patch:  /api/v1/equipment/{equip_id}/status
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.pagination import PaginationParams, get_pagination_params
from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    EquipmentCreate,
    EquipmentRead,
    EquipmentStatusUpdate,
    EquipmentUpdate,
    ProductionLineCreate,
    ProductionLineRead,
    ProductionLineUpdate,
    SiteCreate,
    SiteRead,
    SiteUpdate,
    WorkCellCreate,
    WorkCellRead,
    WorkCellUpdate,
)
from .service import PhysicalModelService

router = APIRouter(prefix="/api/v1", tags=["Physical Model"])
svc = PhysicalModelService


# ─── Sites ────────────────────────────────────────────────────────────


@router.get("/sites")
async def list_sites(
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """List all active sites with cursor-based pagination."""
    items, cursor, has_more = await svc.list_sites(session, params)
    return list_response(
        [SiteRead.model_validate(s).model_dump() for s in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/sites", status_code=201)
async def create_site(
    body: SiteCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.create")),
):
    """Create a new site."""
    site = await svc.create_site(session, **body.model_dump())
    await session.commit()
    return success_response(SiteRead.model_validate(site).model_dump())


@router.get("/sites/{site_id}")
async def get_site(
    site_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """Get a site by ID."""
    site = await svc.get_site(session, site_id)
    return success_response(SiteRead.model_validate(site).model_dump())


@router.put("/sites/{site_id}")
async def update_site(
    site_id: UUID,
    body: SiteUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.update")),
):
    """Update a site."""
    site = await svc.update_site(session, site_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(SiteRead.model_validate(site).model_dump())


@router.delete("/sites/{site_id}", status_code=204)
async def delete_site(
    site_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.delete")),
):
    """Soft-delete a site."""
    await svc.delete_site(session, site_id)
    await session.commit()


# ─── Areas ────────────────────────────────────────────────────────────


@router.get("/sites/{site_id}/areas")
async def list_areas(
    site_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """List areas within a site."""
    items, cursor, has_more = await svc.list_areas_in_site(session, site_id, params)
    return list_response(
        [AreaRead.model_validate(a).model_dump() for a in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/sites/{site_id}/areas", status_code=201)
async def create_area(
    site_id: UUID,
    body: AreaCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.create")),
):
    """Create an area within a site."""
    area = await svc.create_area(session, site_id, **body.model_dump())
    await session.commit()
    return success_response(AreaRead.model_validate(area).model_dump())


@router.get("/areas/{area_id}")
async def get_area(
    area_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """Get an area by ID."""
    area = await svc.get_area(session, area_id)
    return success_response(AreaRead.model_validate(area).model_dump())


@router.put("/areas/{area_id}")
async def update_area(
    area_id: UUID,
    body: AreaUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.update")),
):
    """Update an area."""
    area = await svc.update_area(session, area_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(AreaRead.model_validate(area).model_dump())


# ─── Production Lines ────────────────────────────────────────────────


@router.get("/areas/{area_id}/lines")
async def list_lines(
    area_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """List production lines within an area."""
    items, cursor, has_more = await svc.list_lines_in_area(session, area_id, params)
    return list_response(
        [ProductionLineRead.model_validate(ln).model_dump() for ln in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/areas/{area_id}/lines", status_code=201)
async def create_line(
    area_id: UUID,
    body: ProductionLineCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.create")),
):
    """Create a production line within an area."""
    line = await svc.create_line(session, area_id, **body.model_dump())
    await session.commit()
    return success_response(ProductionLineRead.model_validate(line).model_dump())


@router.get("/lines/{line_id}")
async def get_line(
    line_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """Get a production line by ID."""
    line = await svc.get_line(session, line_id)
    return success_response(ProductionLineRead.model_validate(line).model_dump())


@router.put("/lines/{line_id}")
async def update_line(
    line_id: UUID,
    body: ProductionLineUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.update")),
):
    """Update a production line."""
    line = await svc.update_line(session, line_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(ProductionLineRead.model_validate(line).model_dump())


# ─── Work Cells ───────────────────────────────────────────────────────


@router.get("/lines/{line_id}/work-cells")
async def list_work_cells(
    line_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """List work cells within a production line."""
    items, cursor, has_more = await svc.list_work_cells_in_line(session, line_id, params)
    return list_response(
        [WorkCellRead.model_validate(wc).model_dump() for wc in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/lines/{line_id}/work-cells", status_code=201)
async def create_work_cell(
    line_id: UUID,
    body: WorkCellCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.create")),
):
    """Create a work cell within a production line."""
    wc = await svc.create_work_cell(session, line_id, **body.model_dump())
    await session.commit()
    return success_response(WorkCellRead.model_validate(wc).model_dump())


@router.get("/work-cells/{wc_id}")
async def get_work_cell(
    wc_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """Get a work cell by ID."""
    wc = await svc.get_work_cell(session, wc_id)
    return success_response(WorkCellRead.model_validate(wc).model_dump())


@router.put("/work-cells/{wc_id}")
async def update_work_cell(
    wc_id: UUID,
    body: WorkCellUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.update")),
):
    """Update a work cell."""
    wc = await svc.update_work_cell(session, wc_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(WorkCellRead.model_validate(wc).model_dump())


# ─── Equipment ────────────────────────────────────────────────────────


@router.get("/work-cells/{wc_id}/equipment")
async def list_equipment(
    wc_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """List equipment within a work cell."""
    items, cursor, has_more = await svc.list_equipment_in_work_cell(session, wc_id, params)
    return list_response(
        [EquipmentRead.model_validate(e).model_dump() for e in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/work-cells/{wc_id}/equipment", status_code=201)
async def create_equipment(
    wc_id: UUID,
    body: EquipmentCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.create")),
):
    """Create equipment within a work cell."""
    equip = await svc.create_equipment(session, wc_id, **body.model_dump())
    await session.commit()
    return success_response(EquipmentRead.model_validate(equip).model_dump())


@router.get("/equipment/{equip_id}")
async def get_equipment(
    equip_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.read")),
):
    """Get equipment by ID."""
    equip = await svc.get_equipment(session, equip_id)
    return success_response(EquipmentRead.model_validate(equip).model_dump())


@router.put("/equipment/{equip_id}")
async def update_equipment(
    equip_id: UUID,
    body: EquipmentUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.update")),
):
    """Update equipment fields."""
    equip = await svc.update_equipment(
        session, equip_id, **body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return success_response(EquipmentRead.model_validate(equip).model_dump())


@router.patch("/equipment/{equip_id}/status")
async def update_equipment_status(
    equip_id: UUID,
    body: EquipmentStatusUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("physical_model.update")),
):
    """Update equipment operational status (up/down/idle)."""
    equip = await svc.update_equipment_status(
        session, equip_id, body.status, body.reason
    )
    await session.commit()
    return success_response(EquipmentRead.model_validate(equip).model_dump())
