"""
DEMO: REST endpoints for seeding demonstration scenarios.

POST /api/v1/demo/seed-cpg-erp   → seed ERP-side data (materials, product, BOM, route, orders)
POST /api/v1/demo/seed-cpg-plant → seed plant-side data (site, area, line, work cells, equipment)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import success_response
from mes.framework.db import get_db_session

from .service import seed_erp_data, seed_plant_data
from .service import seed_electronics_erp_data, seed_electronics_plant_data

logger = logging.getLogger("mes.demo")

router = APIRouter(prefix="/api/v1/demo", tags=["Demo"])


@router.post("/seed-cpg-erp")
async def seed_cpg_erp(session: AsyncSession = Depends(get_db_session)):
    """
    One-click seed: create all ERP-side CPG demo data.

    Creates materials, product definition, BOM, process route with
    graph-based step transitions, step parameters (recipe),
    data collection definitions, quality test, and production orders.
    """
    summary = await seed_erp_data(session)
    return success_response(summary)


@router.post("/seed-cpg-plant")
async def seed_cpg_plant(session: AsyncSession = Depends(get_db_session)):
    """
    One-click seed: create the ISA-95 physical hierarchy for the CPG demo.

    Creates site, area, production line, work cells, equipment with
    state models (PackML / SEMI E10), and equipment-material assignments.
    Requires ERP data to be seeded first (materials must exist for
    equipment-material links).
    """
    summary = await seed_plant_data(session)
    return success_response(summary)


@router.post("/seed-electronics-erp")
async def seed_electronics_erp(session: AsyncSession = Depends(get_db_session)):
    """
    One-click seed: create all ERP-side Electronics demo data.

    Creates materials, product definition, BOM, process route with
    graph-based step transitions (AOI rework loop, MRB escalation),
    step parameters, data collection definitions, quality test (FCT),
    and production orders with serial number templates.
    """
    summary = await seed_electronics_erp_data(session)
    return success_response(summary)


@router.post("/seed-electronics-plant")
async def seed_electronics_plant(session: AsyncSession = Depends(get_db_session)):
    """
    One-click seed: create the ISA-95 physical hierarchy for the Electronics demo.

    Creates site, area, production line, work cells, equipment with
    state models (PackML / SEMI E10), and equipment-material assignments.
    Includes dual pick-and-place machines for dispatch demonstration.
    Requires ERP data to be seeded first (materials must exist for
    equipment-material links).
    """
    summary = await seed_electronics_plant_data(session)
    return success_response(summary)
