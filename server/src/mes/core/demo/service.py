"""
Demo: Orchestration service for seeding demonstration scenarios.

Two demos:
  CPG (juice bottling, lot/process tracking):
    - seed_erp_data()   → materials, product, BOM, route, steps, transitions,
                           step params, data defs, quality test, production orders
    - seed_plant_data() → ISA-95 hierarchy, equipment, state models,
                           equipment-material assignments
  Electronics (PCB assembly, unit/serial tracking):
    - seed_electronics_erp_data()  → same structure, discrete mfg
    - seed_electronics_plant_data() → dual pick-and-place, SMT line

All seed functions are fully idempotent — safe to run multiple times.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.material.models import MaterialDefinition, MaterialLot
from mes.core.material.service import MaterialLotService, MaterialService
from mes.core.product_def.models import (
    BillOfMaterial, BOMItem, OperationsDefinition,
    OperationsDefinitionProductAssignment, ProcessSegment,
)
from mes.core.product_def.models import Disposition
from mes.core.product_def.service import ProductDefService
from mes.core.operations.models import OperationsRequest
from mes.core.operations.service import OperationsRequestService
from mes.core.data_collection.models import DataDefinition
from mes.core.data_collection.service import DataDefinitionService
from mes.core.quality.models import QualityTest
from mes.core.quality.service import QualityTestService
from mes.core.physical_model.service import PhysicalModelService
from mes.core.physical_model.models import (
    Site, Area, ProductionLine, WorkCell, Equipment, EquipmentMaterial,
    EquipmentClass, EquipmentClassProperty,
)
from mes.core.inventory.models import StorageLocation
from mes.core.inventory.service import (
    InventoryTransactionService, StorageLocationService,
)
from mes.core.uom.models import UnitOfMeasure
from mes.framework.api.exceptions import MESException

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
                                "process_segments": 0, "transitions": 0,
                                "segment_parameters": 0, "data_definitions": 0,
                                "quality_tests": 0, "material_lots": 0,
                                "dispositions": 0}

    # ── 1. Materials ──────────────────────────────────────────────────
    mat_ids: dict[str, UUID] = {}
    for m in D.MATERIALS:
        mat = await _get_or_create_material(session, m)
        mat_ids[m["code"]] = mat.id
        summary["materials"] += 1

    # ── 1b. Material Lots (initial inventory) ─────────────────────────
    for ml in D.MATERIAL_LOTS:
        mat_id = mat_ids.get(ml["material_code"])
        if mat_id:
            created = await _get_or_create_material_lot(
                session,
                material_id=mat_id,
                lot_number=ml["lot_number"],
                quantity_on_hand=ml["quantity_on_hand"],
                supplier=ml.get("supplier"),
            )
            if created:
                summary["material_lots"] += 1

    # ── 2. Product ────────────────────────────────────────────────────
    product = await _get_or_create_product(session, D.PRODUCT)
    summary["product"] = str(product.id)

    # ── 3. Route ──────────────────────────────────────────────────────
    route, route_created = await _get_or_create_route(
        session, product.id,
        name=D.ROUTE_NAME, version="1.0", is_default=True,
    )

    # ── 4. Dispositions ──────────────────────────────────────────────
    disp_by_code: dict[str, Any] = {}
    for d in D.DISPOSITIONS:
        disp = await _get_or_create_disposition(session, d)
        disp_by_code[d["code"]] = disp
        summary["dispositions"] += 1

    # ── 5. Steps ──────────────────────────────────────────────────────
    step_by_seq: dict[int, Any] = {}

    for s in D.STEPS:
        step_kwargs: dict[str, Any] = {
            "name": s["name"],
            "step_type": s["step_type"],
            "expected_cycle_time_sec": s.get("expected_cycle_time_sec"),
            "erp_operation_number": s.get("erp_operation_number"),
        }
        disp_code = s.get("disposition_code")
        if disp_code and disp_code in disp_by_code:
            step_kwargs["disposition_id"] = disp_by_code[disp_code].id
        step, created = await _get_or_create_step(
            session, route.id, sequence=s["sequence"], **step_kwargs,
        )
        step_by_seq[s["sequence"]] = step
        if created:
            summary["process_segments"] += 1

    # ── 5. BOM (with route_step_id links) ─────────────────────────────
    bom, bom_created = await _get_or_create_bom(session, product.id, version="1.0")
    if bom_created:
        for item in D.BOM_ITEMS:
            item_kwargs = {k: v for k, v in item.items() if k != "step_sequence"}
            step_seq = item.get("step_sequence")
            if step_seq and step_seq in step_by_seq:
                item_kwargs["route_step_id"] = step_by_seq[step_seq].id
            await ProductDefService.create_bom_item(session, bom.id, **item_kwargs)
            summary["bom_items"] += 1
    else:
        # Patch existing BOM items that are missing route_step_id
        result = await session.execute(
            select(BOMItem).where(BOMItem.bom_id == bom.id, BOMItem.is_active.is_(True))
        )
        existing_items = {bi.material_code: bi for bi in result.scalars().all()}
        for item in D.BOM_ITEMS:
            bi = existing_items.get(item["material_code"])
            step_seq = item.get("step_sequence")
            if bi and step_seq and step_seq in step_by_seq and bi.route_step_id is None:
                bi.route_step_id = step_by_seq[step_seq].id

    # ── 6. Transitions ────────────────────────────────────────────────
    if route_created:
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

    # ── 6b. Ensure demo-specific UOMs exist ─────────────────────────
    await _ensure_demo_uoms(session)

    # ── 7. Step Parameters ────────────────────────────────────────────
    if route_created:
        for seq, params in D.STEP_PARAMS.items():
            step = step_by_seq[seq]
            for p in params:
                await ProductDefService.create_step_parameter(session, step.id, **p)
                summary["segment_parameters"] += 1

    # ── 8. Data Collection Definitions ────────────────────────────────
    for seq, defs in D.DATA_DEFS.items():
        step = step_by_seq[seq]
        for d in defs:
            dd = dict(d)
            dd["step_id"] = step.id
            if await _get_or_create_data_def(session, **dd):
                summary["data_definitions"] += 1

    # ── 9. Quality Test ───────────────────────────────────────────────
    qc_step = step_by_seq[30]
    qt_kwargs = dict(D.QUALITY_TEST)
    qt_code = qt_kwargs.pop("code")
    if await _get_or_create_quality_test(
        session, code=qt_code, step_id=qc_step.id, **qt_kwargs,
    ):
        summary["quality_tests"] += 1

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
    site = await _get_or_create_site(session, **D.SITE)
    summary["site"] = str(site.id)

    area = await _get_or_create_area(session, site.id, **D.AREA)
    summary["area"] = str(area.id)

    line = await _get_or_create_line(session, area.id, **D.LINE)
    summary["line"] = str(line.id)

    # ── 2. Work Cells ─────────────────────────────────────────────────
    wc_map: dict[str, UUID] = {}
    for wc in D.WORK_CELLS:
        cell = await _get_or_create_work_cell(session, line.id, **wc)
        wc_map[wc["code"]] = cell.id
        summary["work_cells"] += 1

    # ── 3. Equipment ──────────────────────────────────────────────────
    equip_map: dict[str, UUID] = {}
    for eq in D.EQUIPMENT:
        wc_id = wc_map[eq["work_cell_code"]]
        equip = await _get_or_create_equipment(
            session, wc_id,
            code=eq["code"],
            name=eq["name"],
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
        created = await _get_or_create_equipment_material(
            session, equip_id,
            material_id=mat_id,
            design_speed=em["design_speed"],
            design_speed_uom=em["design_speed_uom"],
            reject_uom=em["reject_uom"],
            target_oee=em["target_oee"],
        )
        if created:
            summary["equipment_materials"] += 1

    # ── 4b. Equipment Classes (ISA-95 Part 2) ─────────────────────────
    ec_counts = await _seed_equipment_classes(session, D, equip_map)
    summary.update(ec_counts)

    # ── 5. Storage Locations ──────────────────────────────────────────
    summary["storage_locations"] = 0
    summary["inventory_received"] = 0

    loc_map: dict[str, UUID] = {}
    for loc in D.STORAGE_LOCATIONS:
        sl = await _get_or_create_storage_location(
            session, site.id, **loc,
        )
        loc_map[loc["code"]] = sl.id
        summary["storage_locations"] += 1

    # ── 6. Receive existing material lots into warehouse storage ──────
    #   For each material lot, do: receive → receiving dock, then putaway → storage
    recv_loc_id = loc_map.get("SB-RECV-01")
    if recv_loc_id:
        lot_rows = await _material_lot_list(session)
        for lot in lot_rows:
            mat_code = lot["material_code"]
            storage_code = D.MATERIAL_STORAGE_MAP.get(mat_code)
            if storage_code is None or lot["quantity_on_hand"] <= 0:
                continue
            storage_loc_id = loc_map.get(storage_code)
            if storage_loc_id is None:
                continue
            # Check if already received (idempotent)
            if await _inventory_already_received(session, lot["lot_id"], storage_loc_id):
                continue
            qty = lot["quantity_on_hand"]
            # Receive into receiving dock
            await InventoryTransactionService.receive(
                session,
                material_lot_id=lot["lot_id"],
                to_location_id=recv_loc_id,
                quantity=qty,
                reason="Demo seed — initial goods receipt",
            )
            # Putaway to warehouse storage
            await InventoryTransactionService.putaway(
                session,
                material_lot_id=lot["lot_id"],
                from_location_id=recv_loc_id,
                to_location_id=storage_loc_id,
                quantity=qty,
                reason="Demo seed — initial putaway",
            )
            summary["inventory_received"] += 1

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
                                "process_segments": 0, "transitions": 0,
                                "segment_parameters": 0, "data_definitions": 0,
                                "quality_tests": 0, "dispositions": 0}

    # ── 1. Materials ──────────────────────────────────────────────────
    mat_ids: dict[str, UUID] = {}
    for m in E.MATERIALS:
        mat = await _get_or_create_material(session, m)
        mat_ids[m["code"]] = mat.id
        summary["materials"] += 1

    # ── 2. Product ────────────────────────────────────────────────────
    product = await _get_or_create_product(session, E.PRODUCT)
    summary["product"] = str(product.id)

    # ── 3. Route ──────────────────────────────────────────────────────
    route, route_created = await _get_or_create_route(
        session, product.id,
        name=E.ROUTE_NAME, version="1.0", is_default=True,
    )

    # ── 4. Dispositions ──────────────────────────────────────────────
    disp_by_code: dict[str, Any] = {}
    for d in E.DISPOSITIONS:
        disp = await _get_or_create_disposition(session, d)
        disp_by_code[d["code"]] = disp
        summary["dispositions"] += 1

    # ── 5. Steps ──────────────────────────────────────────────────────
    step_by_seq: dict[int, Any] = {}

    for s in E.STEPS:
        step_kwargs: dict[str, Any] = {
            "name": s["name"],
            "step_type": s["step_type"],
            "expected_cycle_time_sec": s.get("expected_cycle_time_sec"),
            "erp_operation_number": s.get("erp_operation_number"),
        }
        disp_code = s.get("disposition_code")
        if disp_code and disp_code in disp_by_code:
            step_kwargs["disposition_id"] = disp_by_code[disp_code].id
        step, created = await _get_or_create_step(
            session, route.id, sequence=s["sequence"], **step_kwargs,
        )
        step_by_seq[s["sequence"]] = step
        if created:
            summary["process_segments"] += 1

    # ── 5. BOM (with route_step_id links) ─────────────────────────────
    bom, bom_created = await _get_or_create_bom(session, product.id, version="1.0")
    if bom_created:
        for item in E.BOM_ITEMS:
            item_kwargs = {k: v for k, v in item.items() if k != "step_sequence"}
            step_seq = item.get("step_sequence")
            if step_seq and step_seq in step_by_seq:
                item_kwargs["route_step_id"] = step_by_seq[step_seq].id
            await ProductDefService.create_bom_item(session, bom.id, **item_kwargs)
            summary["bom_items"] += 1
    else:
        # Patch existing BOM items that are missing route_step_id
        result = await session.execute(
            select(BOMItem).where(BOMItem.bom_id == bom.id, BOMItem.is_active.is_(True))
        )
        existing_items = {bi.material_code: bi for bi in result.scalars().all()}
        for item in E.BOM_ITEMS:
            bi = existing_items.get(item["material_code"])
            step_seq = item.get("step_sequence")
            if bi and step_seq and step_seq in step_by_seq and bi.route_step_id is None:
                bi.route_step_id = step_by_seq[step_seq].id

    # ── 6. Transitions ────────────────────────────────────────────────
    if route_created:
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

    # ── 6b. Ensure demo-specific UOMs exist ─────────────────────────
    await _ensure_demo_uoms(session)

    # ── 7. Step Parameters ────────────────────────────────────────────
    if route_created:
        for seq, params in E.STEP_PARAMS.items():
            step = step_by_seq[seq]
            for p in params:
                await ProductDefService.create_step_parameter(session, step.id, **p)
                summary["segment_parameters"] += 1

    # ── 8. Data Collection Definitions ────────────────────────────────
    for seq, defs in E.DATA_DEFS.items():
        step = step_by_seq[seq]
        for d in defs:
            dd = dict(d)
            dd["step_id"] = step.id
            if await _get_or_create_data_def(session, **dd):
                summary["data_definitions"] += 1

    # ── 9. Quality Test ───────────────────────────────────────────────
    fct_step = step_by_seq[60]
    qt_kwargs = dict(E.QUALITY_TEST)
    qt_code = qt_kwargs.pop("code")
    if await _get_or_create_quality_test(
        session, code=qt_code, step_id=fct_step.id, **qt_kwargs,
    ):
        summary["quality_tests"] += 1

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
    site = await _get_or_create_site(session, **E.SITE)
    summary["sites"] += 1

    area = await _get_or_create_area(session, site.id, **E.AREA)
    summary["areas"] += 1

    line = await _get_or_create_line(session, area.id, **E.LINE)
    summary["production_lines"] += 1

    # ── 2. Work Cells ─────────────────────────────────────────────────
    wc_map: dict[str, UUID] = {}
    for wc in E.WORK_CELLS:
        cell = await _get_or_create_work_cell(session, line.id, **wc)
        wc_map[wc["code"]] = cell.id
        summary["work_cells"] += 1

    # ── 3. Equipment ──────────────────────────────────────────────────
    equip_map: dict[str, UUID] = {}
    for eq in E.EQUIPMENT:
        wc_id = wc_map[eq["work_cell_code"]]
        equip = await _get_or_create_equipment(
            session, wc_id,
            code=eq["code"],
            name=eq["name"],
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
        created = await _get_or_create_equipment_material(
            session, equip_id,
            material_id=mat_id,
            design_speed=em["design_speed"],
            design_speed_uom=em["design_speed_uom"],
            reject_uom=em["reject_uom"],
            target_oee=em["target_oee"],
        )
        if created:
            summary["equipment_materials"] += 1

    # ── 4b. Equipment Classes (ISA-95 Part 2) ─────────────────────────
    ec_counts = await _seed_equipment_classes(session, E, equip_map)
    summary.update(ec_counts)

    await session.commit()
    logger.info("Electronics plant demo data seeded: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Helpers — all get-or-create to ensure idempotency
# ---------------------------------------------------------------------------

async def _get_or_create_disposition(
    session: AsyncSession, data: dict,
) -> Disposition:
    """Return existing disposition by code, or create a new one."""
    result = await session.execute(
        select(Disposition).where(Disposition.code == data["code"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    disp = Disposition(**data)
    session.add(disp)
    await session.flush()
    return disp


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


async def _get_or_create_material_lot(
    session: AsyncSession,
    material_id: UUID,
    lot_number: str,
    quantity_on_hand: float,
    supplier: str | None = None,
) -> bool:
    """Return True if a new lot was created, False if it already existed."""
    result = await session.execute(
        select(MaterialLot).where(MaterialLot.lot_number == lot_number)
    )
    if result.scalar_one_or_none():
        return False
    await MaterialLotService.create_lot(
        session,
        material_id=material_id,
        lot_number=lot_number,
        quantity_on_hand=quantity_on_hand,
        supplier=supplier,
    )
    return True


async def _get_or_create_product(session: AsyncSession, data: dict):
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


async def _get_or_create_route(
    session: AsyncSession, product_id: UUID, name: str, **kwargs: Any
) -> tuple[Any, bool]:
    """Return (route, created) — reuses existing route by product+name."""
    result = await session.execute(
        select(OperationsDefinition)
        .join(
            OperationsDefinitionProductAssignment,
            OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
        )
        .where(
            OperationsDefinitionProductAssignment.product_id == product_id,
            OperationsDefinitionProductAssignment.is_active.is_(True),
            OperationsDefinition.name == name,
            OperationsDefinition.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False
    route = await ProductDefService.create_route(session, product_id, name=name, **kwargs)
    return route, True


async def _get_or_create_bom(
    session: AsyncSession, product_id: UUID, version: str = "1.0",
) -> tuple[Any, bool]:
    """Return (bom, created) — reuses existing BOM by product+version."""
    result = await session.execute(
        select(BillOfMaterial).where(
            BillOfMaterial.product_id == product_id,
            BillOfMaterial.version == version,
            BillOfMaterial.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False
    bom = await ProductDefService.create_bom(session, product_id, version=version)
    return bom, True


async def _get_or_create_step(
    session: AsyncSession, route_id: UUID, sequence: int, **kwargs: Any
) -> tuple[Any, bool]:
    """Return (step, created) — reuses existing step by route+sequence."""
    result = await session.execute(
        select(ProcessSegment).where(
            ProcessSegment.route_id == route_id,
            ProcessSegment.sequence == sequence,
            ProcessSegment.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False
    step = await ProductDefService.create_step(session, route_id, sequence=sequence, **kwargs)
    return step, True


async def _get_or_create_order(
    session: AsyncSession, order_number: str, **kwargs: Any
) -> bool:
    """Create order if it doesn't exist. Returns True if created."""
    result = await session.execute(
        select(OperationsRequest.id).where(OperationsRequest.order_number == order_number)
    )
    if result.scalar_one_or_none() is not None:
        return False
    await OperationsRequestService.create_order(session, order_number=order_number, **kwargs)
    return True


async def _get_or_create_data_def(
    session: AsyncSession, code: str, **kwargs: Any
) -> bool:
    """Create data definition if code doesn't exist. Returns True if created."""
    result = await session.execute(
        select(DataDefinition.id).where(DataDefinition.code == code)
    )
    if result.scalar_one_or_none() is not None:
        return False
    await DataDefinitionService.create_definition(session, code=code, **kwargs)
    return True


async def _get_or_create_quality_test(
    session: AsyncSession, code: str, **kwargs: Any
) -> bool:
    """Create quality test if code doesn't exist. Returns True if created."""
    result = await session.execute(
        select(QualityTest.id).where(QualityTest.code == code)
    )
    if result.scalar_one_or_none() is not None:
        return False
    await QualityTestService.create_test(session, code=code, **kwargs)
    return True


async def _get_or_create_site(session: AsyncSession, **kwargs: Any) -> Any:
    """Return existing site by code, or create."""
    result = await session.execute(
        select(Site).where(Site.code == kwargs["code"], Site.is_active.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_site(session, **kwargs)


async def _get_or_create_area(session: AsyncSession, site_id: UUID, **kwargs: Any) -> Any:
    """Return existing area by code, or create."""
    result = await session.execute(
        select(Area).where(Area.code == kwargs["code"], Area.is_active.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_area(session, site_id, **kwargs)


async def _get_or_create_line(session: AsyncSession, area_id: UUID, **kwargs: Any) -> Any:
    """Return existing production line by code, or create."""
    result = await session.execute(
        select(ProductionLine).where(
            ProductionLine.code == kwargs["code"], ProductionLine.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_line(session, area_id, **kwargs)


async def _get_or_create_work_cell(session: AsyncSession, line_id: UUID, **kwargs: Any) -> Any:
    """Return existing work cell by code, or create."""
    result = await session.execute(
        select(WorkCell).where(WorkCell.code == kwargs["code"], WorkCell.is_active.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_work_cell(session, line_id, **kwargs)


async def _get_or_create_equipment(session: AsyncSession, wc_id: UUID, **kwargs: Any) -> Any:
    """Return existing equipment by code, or create."""
    result = await session.execute(
        select(Equipment).where(Equipment.code == kwargs["code"], Equipment.is_active.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_equipment(session, wc_id, **kwargs)


async def _get_or_create_equipment_material(
    session: AsyncSession, equip_id: UUID, **kwargs: Any,
) -> bool:
    """Create equipment-material if it doesn't exist. Returns True if created."""
    result = await session.execute(
        select(EquipmentMaterial.id).where(
            EquipmentMaterial.equipment_id == equip_id,
            EquipmentMaterial.material_id == kwargs["material_id"],
            EquipmentMaterial.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is not None:
        return False
    await PhysicalModelService.create_equipment_material(session, equip_id, **kwargs)
    return True




async def _material_id_map(session: AsyncSession) -> dict[str, UUID]:
    """Return {code: id} for all active materials."""
    result = await session.execute(
        select(MaterialDefinition.code, MaterialDefinition.id).where(
            MaterialDefinition.is_active.is_(True)
        )
    )
    return {row[0]: row[1] for row in result.all()}


# Demo-specific UOMs not in the standard seed data.
# Each entry: (symbol, name, uom_type, multiplier, offset)
_DEMO_UOMS: list[tuple[str, str, str, float, float]] = [
    ("°Bx",    "degrees Brix",         "concentration", 1.0, 0.0),
    ("pH",     "pH",                   "concentration", 1.0, 0.0),
    ("CFU/mL", "colony-forming units per mL", "concentration", 1.0, 0.0),
    ("mL",     "millilitre",           "volume",        0.001, 0.0),
    ("mm",     "millimetre",           "length",        0.001, 0.0),
    ("Nm",     "newton-metre",         "torque",        1.0, 0.0),
    ("count",  "count",                "count",         1.0, 0.0),
    ("V",      "volt",                 "electrical",    1.0, 0.0),
    ("mA",     "milliampere",          "electrical",    0.001, 0.0),
    ("kPa",    "kilopascal",           "pressure",      1000.0, 0.0),
    ("µm",     "micrometre",           "length",        1e-6, 0.0),
    ("cph",    "components per hour",  "rate",          1.0, 0.0),
    ("mm/s",   "millimetres per second", "rate",        0.001, 0.0),
    ("mm/min", "millimetres per minute", "rate",        0.001 / 60, 0.0),
]


async def _ensure_demo_uoms(session: AsyncSession) -> None:
    """Create any demo-specific UOMs that are not already in the DB."""
    result = await session.execute(select(UnitOfMeasure.symbol))
    existing = {row[0] for row in result.all()}

    for symbol, name, uom_type, multiplier, offset in _DEMO_UOMS:
        if symbol not in existing:
            session.add(UnitOfMeasure(
                symbol=symbol,
                name=name,
                uom_type=uom_type,
                multiplier=multiplier,
                offset=offset,
                is_builtin=False,
            ))
    await session.flush()


async def _get_or_create_storage_location(
    session: AsyncSession, site_id: UUID, **kwargs: Any,
) -> StorageLocation:
    """Get existing or create new storage location (idempotent by code)."""
    code = kwargs["code"]
    result = await session.execute(
        select(StorageLocation).where(StorageLocation.code == code),
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing
    loc = StorageLocation(site_id=site_id, **kwargs)
    session.add(loc)
    await session.flush()
    return loc


async def _material_lot_list(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Return list of {lot_id, material_code, quantity_on_hand} for all active lots."""
    result = await session.execute(
        select(
            MaterialLot.id,
            MaterialDefinition.code,
            MaterialLot.quantity_on_hand,
        )
        .join(MaterialDefinition, MaterialLot.material_id == MaterialDefinition.id)
        .where(MaterialLot.is_active.is_(True)),
    )
    return [
        {"lot_id": row[0], "material_code": row[1], "quantity_on_hand": row[2]}
        for row in result.all()
    ]


async def _inventory_already_received(
    session: AsyncSession, lot_id: UUID, location_id: UUID,
) -> bool:
    """Check if an inventory balance already exists for this lot+location pair."""
    from mes.core.inventory.models import InventoryBalance
    result = await session.execute(
        select(InventoryBalance.id).where(
            InventoryBalance.material_lot_id == lot_id,
            InventoryBalance.location_id == location_id,
        ),
    )
    return result.scalar_one_or_none() is not None


async def _get_or_create_equipment_class(
    session: AsyncSession, **kwargs: Any,
) -> EquipmentClass:
    """Return existing equipment class by code, or create."""
    result = await session.execute(
        select(EquipmentClass).where(
            EquipmentClass.code == kwargs["code"],
            EquipmentClass.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_equipment_class(session, **kwargs)


async def _get_or_create_class_property(
    session: AsyncSession, class_id: UUID, **kwargs: Any,
) -> EquipmentClassProperty:
    """Return existing class property by (class_id, name), or create."""
    result = await session.execute(
        select(EquipmentClassProperty).where(
            EquipmentClassProperty.equipment_class_id == class_id,
            EquipmentClassProperty.name == kwargs["name"],
            EquipmentClassProperty.is_active.is_(True),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await PhysicalModelService.create_class_property(session, class_id, **kwargs)


async def _seed_equipment_classes(
    session: AsyncSession,
    data_module: Any,
    equip_map: dict[str, UUID],
) -> dict[str, int]:
    """Seed equipment classes, properties, and assign classes to equipment.
    Returns counts summary."""
    counts = {"equipment_classes": 0, "class_properties": 0, "class_assignments": 0}

    if not hasattr(data_module, "EQUIPMENT_CLASSES"):
        return counts

    # Create classes
    class_map: dict[str, UUID] = {}
    for ec_data in data_module.EQUIPMENT_CLASSES:
        ec = await _get_or_create_equipment_class(session, **ec_data)
        class_map[ec_data["code"]] = ec.id
        counts["equipment_classes"] += 1

    # Create properties
    if hasattr(data_module, "EQUIPMENT_CLASS_PROPERTIES"):
        for prop_data in data_module.EQUIPMENT_CLASS_PROPERTIES:
            pdata = dict(prop_data)
            class_code = pdata.pop("class_code")
            class_id = class_map[class_code]
            await _get_or_create_class_property(session, class_id, **pdata)
            counts["class_properties"] += 1

    # Assign classes to equipment
    if hasattr(data_module, "EQUIPMENT_CLASS_MAP"):
        for equip_code, class_code in data_module.EQUIPMENT_CLASS_MAP.items():
            equip_id = equip_map.get(equip_code)
            class_id = class_map.get(class_code)
            if equip_id and class_id:
                result = await session.execute(
                    select(Equipment).where(Equipment.id == equip_id)
                )
                equip = result.scalar_one_or_none()
                if equip and equip.equipment_class_id != class_id:
                    equip.equipment_class_id = class_id
                    counts["class_assignments"] += 1
        await session.flush()

    return counts
