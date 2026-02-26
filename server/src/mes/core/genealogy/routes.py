"""
GENEALOGY: REST API routes for product genealogy/traceability.

Endpoints:
- GET /api/v1/units/{unit_id}/genealogy   Get full as-built record for a unit
- GET /api/v1/lots/{lot_id}/genealogy     Get full as-built record for a lot
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .service import GenealogyService

router = APIRouter(prefix="/api/v1", tags=["Genealogy"])


@router.get("/units/{unit_id}/genealogy")
async def get_unit_genealogy(
    unit_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("genealogy.read")),
):
    """Get the full as-built traceability record for a unit."""
    record = await GenealogyService.get_unit_genealogy(session, unit_id)
    return success_response(record.model_dump())


@router.get("/lots/{lot_id}/genealogy")
async def get_lot_genealogy(
    lot_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("genealogy.read")),
):
    """Get the full as-built traceability record for a lot."""
    record = await GenealogyService.get_lot_genealogy(session, lot_id)
    return success_response(record.model_dump())
