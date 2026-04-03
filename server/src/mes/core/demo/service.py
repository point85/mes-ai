"""
CPG Demo: Orchestration service for seeding the juice-bottling demo.

Two entry points:
  - seed_erp_data()   → materials, product, BOM, route, steps, transitions,
                         step params, data defs, quality test, production orders
  - seed_plant_data() → ISA-95 hierarchy, equipment, state models,
                         equipment-material assignments
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.material.models import MaterialDefinition
from mes.core.material.service import MaterialService
from mes.core.product_def.service import ProductDefService
from mes.core.production.service import ProductionOrderService
from mes.core.data_collection.service import DataDefinitionService
from mes.core.quality.service import QualityTestService
from mes.core.physical_model.service import PhysicalModelService
from mes.core.physical_model.models import WorkCell, Equipment

from . import cpg_data as D
from . import electronics_data as E

logger = logging.getLogger("mes.demo")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def seed_erp_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create all ERP-side master data for the CPG demo.

    Returns a summary dict with counts and created IDs.
    """
    summary: dict[str, Any] = {"materials": 0, "product": None, "bom_items": 0,
                                "route_steps": 0, "transitions": 0,
                                "step_parameters": 0, "data_definitions": 0,
                                "quality_tests": 0, "production_orders": 0}

    # ── 1. Materials ──────────────────────────────────────────────────
    mat_ids: dict[str, UUID] = {}
    for m in D.MATERIALS:
        mat = await _get_or_create_material(session, m)
        mat_ids[m["code"]] = mat.id
        summary["materials"] += 1

    # ── 2. Product ────────────────────────────────────────────────────
    product = await _get_or_create_product(session, D.PRODUCT)
    summary["product"] = str(product.id)

    # ── 3. BOM ────────────────────────────────────────────────────────
    bom = await ProductDefService.create_bom(
        session, product.id, version="1.0",
    )
    for item in D.BOM_ITEMS:
        await ProductDefService.create_bom_item(session, bom.id, **item)
        summary["bom_items"] += 1

    # ── 4. Route ──────────────────────────────────────────────────────
    route = await ProductDefService.create_route(
        session, product.id,
        name=D.ROUTE_NAME, version="1.0", is_default=True,
    )

    # ── 5. Steps ──────────────────────────────────────────────────────
    step_by_seq: dict[int, Any] = {}
    wc_ids = await _work_cell_id_map(session)

    for s in D.STEPS:
        step_kwargs: dict[str, Any] = {
            "sequence": s["sequence"],
            "name": s["name"],
            "step_type": s["step_type"],
            "expected_cycle_time_sec": s.get("expected_cycle_time_sec"),
            "erp_operation_number": s.get("erp_operation_number"),
        }
        wc_code = s.get("work_cell_code")
        if wc_code and wc_code in wc_ids:
            step_kwargs["work_cell_id"] = wc_ids[wc_code]
        step = await ProductDefService.create_step(session, route.id, **step_kwargs)
        step_by_seq[s["sequence"]] = step
        summary["route_steps"] += 1

    # ── 6. Transitions ────────────────────────────────────────────────
    for t in D.TRANSITIONS:
        from_step = step_by_seq[t["from_seq"]]
        to_step   = step_by_seq[t["to_seq"]]
        await ProductDefService.create_step_transition(
            session, from_step.id,
            to_step_id=to_step.id,
            condition=t["condition"],
            priority=t["priority"],
            is_default=t["is_default"],
            label=t["label"],
        )
        summary["transitions"] += 1

    # ── 7. Step Parameters ────────────────────────────────────────────
    for seq, params in D.STEP_PARAMS.items():
        step = step_by_seq[seq]
        for p in params:
            await ProductDefService.create_step_parameter(session, step.id, **p)
            summary["step_parameters"] += 1

    # ── 8. Data Collection Definitions ────────────────────────────────
    for seq, defs in D.DATA_DEFS.items():
        step = step_by_seq[seq]
        for d in defs:
            dd = dict(d)
            dd["step_id"] = step.id
            await DataDefinitionService.create_definition(session, **dd)
            summary["data_definitions"] += 1

    # ── 9. Quality Test ───────────────────────────────────────────────
    qc_step = step_by_seq[30]
    await QualityTestService.create_test(
        session,
        step_id=qc_step.id,
        **D.QUALITY_TEST,
    )
    summary["quality_tests"] += 1

    # ── 10. Production Orders ─────────────────────────────────────────
    for o in D.ORDERS:
        await ProductionOrderService.create_order(
            session,
            product_id=product.id,
            route_id=route.id,
            **o,
        )
        summary["production_orders"] += 1

    await session.commit()
    logger.info("CPG ERP demo data seeded: %s", summary)
    return summary


async def seed_plant_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create the ISA-95 physical hierarchy, assign equipment state models,
    and set up equipment-material assignments.

    Returns a summary dict with counts.
    """
    summary: dict[str, Any] = {"site": None, "area": None, "line": None,
                                "work_cells": 0, "equipment": 0,
                                "equipment_materials": 0}

    # ── 1. Site → Area → Line ─────────────────────────────────────────
    site = await PhysicalModelService.create_site(session, **D.SITE)
    summary["site"] = str(site.id)

    area = await PhysicalModelService.create_area(session, site.id, **D.AREA)
    summary["area"] = str(area.id)

    line = await PhysicalModelService.create_line(session, area.id, **D.LINE)
    summary["line"] = str(line.id)

    # ── 2. Work Cells ─────────────────────────────────────────────────
    wc_map: dict[str, UUID] = {}
    for wc in D.WORK_CELLS:
        cell = await PhysicalModelService.create_work_cell(session, line.id, **wc)
        wc_map[wc["code"]] = cell.id
        summary["work_cells"] += 1

    # ── 3. Equipment ──────────────────────────────────────────────────
    equip_map: dict[str, UUID] = {}
    for eq in D.EQUIPMENT:
        wc_id = wc_map[eq["work_cell_code"]]
        equip = await PhysicalModelService.create_equipment(
            session, wc_id,
            code=eq["code"],
            name=eq["name"],
            equipment_type=eq.get("equipment_type"),
            state_model_id=eq.get("state_model"),
            max_queue_depth=eq.get("max_queue_depth"),
        )
        equip_map[eq["code"]] = equip.id
        summary["equipment"] += 1

    # ── 4. Equipment–Material assignments ─────────────────────────────
    mat_ids = await _material_id_map(session)

    for em in D.EQUIPMENT_MATERIALS:
        equip_id = equip_map[em["equipment_code"]]
        mat_id = mat_ids.get(em["material_code"])
        if mat_id is None:
            logger.warning(
                "Material %s not found — skipping equipment-material setup for %s",
                em["material_code"], em["equipment_code"],
            )
            continue
        await PhysicalModelService.create_equipment_material(
            session, equip_id,
            material_id=mat_id,
            design_speed=em["design_speed"],
            design_speed_uom=em["design_speed_uom"],
            reject_uom=em["reject_uom"],
            target_oee=em["target_oee"],
        )
        summary["equipment_materials"] += 1

    await session.commit()
    logger.info("CPG plant demo data seeded: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Electronics Demo — PCB Assembly Line (unit / serial-number tracking)
# ---------------------------------------------------------------------------

async def seed_electronics_erp_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create all ERP-side master data for the Electronics demo.

    Returns a summary dict with counts and created IDs.
    """
    summary: dict[str, Any] = {"materials": 0, "product": None, "bom_items": 0,
                                "route_steps": 0, "transitions": 0,
                                "step_parameters": 0, "data_definitions": 0,
                                "quality_tests": 0, "production_orders": 0}

    # ── 1. Materials ──────────────────────────────────────────────────
    mat_ids: dict[str, UUID] = {}
    for m in E.MATERIALS:
        mat = await _get_or_create_material(session, m)
        mat_ids[m["code"]] = mat.id
        summary["materials"] += 1

    # ── 2. Product ────────────────────────────────────────────────────
    product = await _get_or_create_product(session, E.PRODUCT)
    summary["product"] = str(product.id)

    # ── 3. BOM ────────────────────────────────────────────────────────
    bom = await ProductDefService.create_bom(
        session, product.id, version="1.0",
    )
    for item in E.BOM_ITEMS:
        await ProductDefService.create_bom_item(session, bom.id, **item)
        summary["bom_items"] += 1

    # ── 4. Route ──────────────────────────────────────────────────────
    route = await ProductDefService.create_route(
        session, product.id,
        name=E.ROUTE_NAME, version="1.0", is_default=True,
    )

    # ── 5. Steps ──────────────────────────────────────────────────────
    step_by_seq: dict[int, Any] = {}
    wc_ids = await _work_cell_id_map(session)

    for s in E.STEPS:
        step_kwargs: dict[str, Any] = {
            "sequence": s["sequence"],
            "name": s["name"],
            "step_type": s["step_type"],
            "expected_cycle_time_sec": s.get("expected_cycle_time_sec"),
            "erp_operation_number": s.get("erp_operation_number"),
        }
        wc_code = s.get("work_cell_code")
        if wc_code and wc_code in wc_ids:
            step_kwargs["work_cell_id"] = wc_ids[wc_code]
        step = await ProductDefService.create_step(session, route.id, **step_kwargs)
        step_by_seq[s["sequence"]] = step
        summary["route_steps"] += 1

    # ── 6. Transitions ────────────────────────────────────────────────
    for t in E.TRANSITIONS:
        from_step = step_by_seq[t["from_seq"]]
        to_step   = step_by_seq[t["to_seq"]]
        await ProductDefService.create_step_transition(
            session, from_step.id,
            to_step_id=to_step.id,
            condition=t["condition"],
            priority=t["priority"],
            is_default=t["is_default"],
            label=t["label"],
        )
        summary["transitions"] += 1

    # ── 7. Step Parameters ────────────────────────────────────────────
    for seq, params in E.STEP_PARAMS.items():
        step = step_by_seq[seq]
        for p in params:
            await ProductDefService.create_step_parameter(session, step.id, **p)
            summary["step_parameters"] += 1

    # ── 8. Data Collection Definitions ────────────────────────────────
    for seq, defs in E.DATA_DEFS.items():
        step = step_by_seq[seq]
        for d in defs:
            dd = dict(d)
            dd["step_id"] = step.id
            await DataDefinitionService.create_definition(session, **dd)
            summary["data_definitions"] += 1

    # ── 9. Quality Test ───────────────────────────────────────────────
    fct_step = step_by_seq[60]
    await QualityTestService.create_test(
        session,
        step_id=fct_step.id,
        **E.QUALITY_TEST,
    )
    summary["quality_tests"] += 1

    # ── 10. Production Orders ─────────────────────────────────────────
    for o in E.ORDERS:
        await ProductionOrderService.create_order(
            session,
            product_id=product.id,
            route_id=route.id,
            **o,
        )
        summary["production_orders"] += 1

    await session.commit()
    logger.info("Electronics ERP demo data seeded: %s", summary)
    return summary


async def seed_electronics_plant_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create the ISA-95 physical hierarchy for the Electronics demo.

    Returns a summary dict with counts.
    """
    summary: dict[str, Any] = {"sites": 0, "areas": 0,
                                "production_lines": 0, "work_cells": 0,
                                "equipment": 0, "equipment_materials": 0}

    # ── 1. Site → Area → Line ─────────────────────────────────────────
    site = await PhysicalModelService.create_site(session, **E.SITE)
    summary["sites"] += 1

    area = await PhysicalModelService.create_area(session, site.id, **E.AREA)
    summary["areas"] += 1

    line = await PhysicalModelService.create_line(session, area.id, **E.LINE)
    summary["production_lines"] += 1

    # ── 2. Work Cells ─────────────────────────────────────────────────
    wc_map: dict[str, UUID] = {}
    for wc in E.WORK_CELLS:
        cell = await PhysicalModelService.create_work_cell(session, line.id, **wc)
        wc_map[wc["code"]] = cell.id
        summary["work_cells"] += 1

    # ── 3. Equipment ──────────────────────────────────────────────────
    equip_map: dict[str, UUID] = {}
    for eq in E.EQUIPMENT:
        wc_id = wc_map[eq["work_cell_code"]]
        equip = await PhysicalModelService.create_equipment(
            session, wc_id,
            code=eq["code"],
            name=eq["name"],
            equipment_type=eq.get("equipment_type"),
            state_model_id=eq.get("state_model"),
            max_queue_depth=eq.get("max_queue_depth"),
        )
        equip_map[eq["code"]] = equip.id
        summary["equipment"] += 1

    # ── 4. Equipment–Material assignments ─────────────────────────────
    mat_ids = await _material_id_map(session)

    for em in E.EQUIPMENT_MATERIALS:
        equip_id = equip_map[em["equipment_code"]]
        mat_id = mat_ids.get(em["material_code"])
        if mat_id is None:
            logger.warning(
                "Material %s not found — skipping equipment-material setup for %s",
                em["material_code"], em["equipment_code"],
            )
            continue
        await PhysicalModelService.create_equipment_material(
            session, equip_id,
            material_id=mat_id,
            design_speed=em["design_speed"],
            design_speed_uom=em["design_speed_uom"],
            reject_uom=em["reject_uom"],
            target_oee=em["target_oee"],
        )
        summary["equipment_materials"] += 1

    await session.commit()
    logger.info("Electronics plant demo data seeded: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_material(
    session: AsyncSession, data: dict,
) -> MaterialDefinition:
    """Return existing material by code, or create a new one."""
    result = await session.execute(
        select(MaterialDefinition).where(MaterialDefinition.code == data["code"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await MaterialService.create_material(session, **data)


async def _get_or_create_product(session, data: dict):
    """Return existing product by code+version, or create a new one."""
    from mes.core.product_def.models import ProductDefinition
    result = await session.execute(
        select(ProductDefinition).where(
            ProductDefinition.code == data["code"],
            ProductDefinition.version == data.get("version", "1.0"),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await ProductDefService.create_product(session, **data)


async def _work_cell_id_map(session: AsyncSession) -> dict[str, UUID]:
    """Return {code: id} for all active work cells."""
    result = await session.execute(
        select(WorkCell.code, WorkCell.id).where(WorkCell.is_active.is_(True))
    )
    return {row[0]: row[1] for row in result.all()}


async def _material_id_map(session: AsyncSession) -> dict[str, UUID]:
    """Return {code: id} for all active materials."""
    result = await session.execute(
        select(MaterialDefinition.code, MaterialDefinition.id).where(
            MaterialDefinition.is_active.is_(True)
        )
    )
    return {row[0]: row[1] for row in result.all()}
