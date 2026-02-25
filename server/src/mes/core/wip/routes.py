"""
WIP-TRACK: REST API routes for work-in-process tracking.

Endpoints — Units:
- GET    /api/v1/units                     List units
- POST   /api/v1/units                     Create a unit
- GET    /api/v1/units/{unit_id}           Get a unit
- POST   /api/v1/units/{unit_id}/start     Start processing at current step
- POST   /api/v1/units/{unit_id}/complete  Complete current step
- POST   /api/v1/units/{unit_id}/move      Move to next step
- POST   /api/v1/units/{unit_id}/hold      Place on hold
- POST   /api/v1/units/{unit_id}/release-hold  Release from hold
- POST   /api/v1/units/{unit_id}/scrap     Scrap the unit
- GET    /api/v1/units/{unit_id}/history   Get processing history

Endpoints — Lots:
- GET    /api/v1/lots                      List lots
- POST   /api/v1/lots                      Create a lot
- GET    /api/v1/lots/{lot_id}             Get a lot
- POST   /api/v1/lots/{lot_id}/start       Start processing
- POST   /api/v1/lots/{lot_id}/complete    Complete current step
- POST   /api/v1/lots/{lot_id}/move        Move to next step
- GET    /api/v1/lots/{lot_id}/history     Get processing history
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
    UnitCreate, UnitRead, UnitHistoryRead,
    LotCreate, LotRead, LotHistoryRead,
    StartRequest, CompleteRequest, MoveRequest,
    HoldRequest, ScrapRequest,
)
from .service import UnitService, LotService

router = APIRouter(prefix="/api/v1", tags=["WIP Tracking"])


# ═══════════════════════════════════════════════════════════════════
# UNIT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.get("/units")
async def list_units(
    status: str | None = Query(None),
    order_id: UUID | None = Query(None),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.read")),
):
    """List active units with optional filters."""
    items, cursor, has_more = await UnitService.list_units(
        session, params, status=status, order_id=order_id,
    )
    return list_response(
        [UnitRead.model_validate(u).model_dump() for u in items],
        cursor=cursor, limit=params.limit, has_more=has_more,
    )


@router.post("/units", status_code=201)
async def create_unit(
    body: UnitCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.create")),
):
    """Create a new unit under a released production order."""
    unit = await UnitService.create_unit(session, **body.model_dump())
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.get("/units/{unit_id}")
async def get_unit(
    unit_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.read")),
):
    """Get a unit by ID."""
    unit = await UnitService.get_unit(session, unit_id)
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.post("/units/{unit_id}/start")
async def start_unit(
    unit_id: UUID,
    body: StartRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Start processing a unit at its current (or first) step."""
    eq_id = body.equipment_id if body else None
    unit = await UnitService.start_unit(session, unit_id, equipment_id=eq_id)
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.post("/units/{unit_id}/complete")
async def complete_unit(
    unit_id: UUID,
    body: CompleteRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Complete the current step for a unit."""
    result = body.result if body else "pass"
    data = body.data_snapshot if body else None
    unit = await UnitService.complete_unit_step(
        session, unit_id, result=result, data_snapshot=data,
    )
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.post("/units/{unit_id}/move")
async def move_unit(
    unit_id: UUID,
    body: MoveRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Move a unit to the next step (or a specific target step)."""
    target = body.target_step_id if body else None
    unit = await UnitService.move_unit(session, unit_id, target_step_id=target)
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.post("/units/{unit_id}/hold")
async def hold_unit(
    unit_id: UUID,
    body: HoldRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Place a unit on hold."""
    unit = await UnitService.hold_unit(session, unit_id, reason=body.reason)
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.post("/units/{unit_id}/release-hold")
async def release_hold_unit(
    unit_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Release a unit from hold."""
    unit = await UnitService.release_hold_unit(session, unit_id)
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.post("/units/{unit_id}/scrap")
async def scrap_unit(
    unit_id: UUID,
    body: ScrapRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Scrap a unit."""
    unit = await UnitService.scrap_unit(session, unit_id, reason=body.reason)
    await session.commit()
    return success_response(UnitRead.model_validate(unit).model_dump())


@router.get("/units/{unit_id}/history")
async def get_unit_history(
    unit_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.read")),
):
    """Get processing history for a unit."""
    records = await UnitService.get_unit_history(session, unit_id)
    return success_response(
        [UnitHistoryRead.model_validate(r).model_dump() for r in records]
    )


# ═══════════════════════════════════════════════════════════════════
# LOT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.get("/lots")
async def list_lots(
    status: str | None = Query(None),
    order_id: UUID | None = Query(None),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.read")),
):
    """List active lots with optional filters."""
    items, cursor, has_more = await LotService.list_lots(
        session, params, status=status, order_id=order_id,
    )
    return list_response(
        [LotRead.model_validate(l).model_dump() for l in items],
        cursor=cursor, limit=params.limit, has_more=has_more,
    )


@router.post("/lots", status_code=201)
async def create_lot(
    body: LotCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.create")),
):
    """Create a new lot under a released production order."""
    lot = await LotService.create_lot(session, **body.model_dump())
    await session.commit()
    return success_response(LotRead.model_validate(lot).model_dump())


@router.get("/lots/{lot_id}")
async def get_lot(
    lot_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.read")),
):
    """Get a lot by ID."""
    lot = await LotService.get_lot(session, lot_id)
    return success_response(LotRead.model_validate(lot).model_dump())


@router.post("/lots/{lot_id}/start")
async def start_lot(
    lot_id: UUID,
    body: StartRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Start processing a lot at its current (or first) step."""
    eq_id = body.equipment_id if body else None
    lot = await LotService.start_lot(session, lot_id, equipment_id=eq_id)
    await session.commit()
    return success_response(LotRead.model_validate(lot).model_dump())


@router.post("/lots/{lot_id}/complete")
async def complete_lot(
    lot_id: UUID,
    body: CompleteRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Complete the current step for a lot."""
    qty_out = body.quantity_out if body else None
    qty_scrapped = body.quantity_scrapped if body else 0
    lot = await LotService.complete_lot_step(
        session, lot_id,
        quantity_out=qty_out,
        quantity_scrapped=qty_scrapped or 0,
    )
    await session.commit()
    return success_response(LotRead.model_validate(lot).model_dump())


@router.post("/lots/{lot_id}/move")
async def move_lot(
    lot_id: UUID,
    body: MoveRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.update")),
):
    """Move a lot to the next step (or a specific target step)."""
    target = body.target_step_id if body else None
    lot = await LotService.move_lot(session, lot_id, target_step_id=target)
    await session.commit()
    return success_response(LotRead.model_validate(lot).model_dump())


@router.get("/lots/{lot_id}/history")
async def get_lot_history(
    lot_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("wip.read")),
):
    """Get processing history for a lot."""
    records = await LotService.get_lot_history(session, lot_id)
    return success_response(
        [LotHistoryRead.model_validate(r).model_dump() for r in records]
    )
