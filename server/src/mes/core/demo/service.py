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
    EquipmentClass, EquipmentClassProperty, EquipmentCapability,
)
from mes.core.inventory.models import StorageLocation
from mes.core.inventory.service import (
    InventoryTransactionService, StorageLocationService,
)
from datetime import date, time, timedelta

from mes.core.uom.models import UnitOfMeasure
from mes.core.work_schedule.models import WorkSchedule as _WorkScheduleModel
from mes.core.work_schedule.service import WorkScheduleService as _WorkScheduleSvc
from mes.framework.api.exceptions import MESException, ValidationException

from . import cpg_data as D
from . import electronics_data as E

logger = logging.getLogger("mes.demo")


# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------

async def _require_erp_seed(
    session: AsyncSession,
    *,
    scenario: str,
    route_name: str,
    erp_endpoint: str,
) -> None:
    """
    Ensure the ERP-side seed (materials, product, route, segments) has been
    run for this scenario before the plant-side seed executes.

    The plant seed resolves ProcessSegment and MaterialDefinition rows by
    code/name when building SegmentEquipmentClassAssignment,
    SegmentEquipmentRequirement, SegmentMaterialRequirement, and
    EquipmentMaterial. If those rows don't exist, the plant seed will fail
    mid-way with opaque FK errors. We detect the missing prerequisite up
    front and return a clear 422 instead.
    """
    result = await session.execute(
        select(OperationsDefinition.id).where(
            OperationsDefinition.name == route_name,
            OperationsDefinition.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise ValidationException(
            message=(
                f"Cannot seed the {scenario} plant model: the {scenario} ERP "
                f"data has not been seeded yet. Run the ERP-side seed first "
                f"(POST {erp_endpoint} — 'Seed {scenario} Demo' on the ERP "
                f"Simulator Dashboard), then retry this request."
            ),
            details={
                "scenario": scenario,
                "missing_route": route_name,
                "required_first": erp_endpoint,
            },
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def seed_erp_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create all ERP-side master data for the CPG demo.

    Returns a summary dict with counts and created IDs.
    """
    summary: dict[str, Any] = {"materials": 0, "product": None, "bom_items": 0,
                                "process_segments": 0,
                                "input_disposition_links": 0,
                                "output_disposition_links": 0,
                                "segment_parameters": 0, "data_definitions": 0,
                                "quality_tests": 0, "material_lots": 0,
                                "dispositions": 0,
                                "segment_material_requirements": 0,
                                "route_material_assignments": 0}

    # ── 0. Ensure demo-specific UOMs exist (°Bx, pH, CFU/mL, ...) ───
    # Must run BEFORE materials — MaterialDefinition.uom_id has an FK to
    # units_of_measure.id.
    await _ensure_demo_uoms(session)
    uom_ids = await _uom_id_map(session)

    # ── 1. Materials ──────────────────────────────────────────────────
    mat_ids: dict[str, UUID] = {}
    for m in D.MATERIALS:
        mat = await _get_or_create_material(session, _inject_uom_id(m, uom_ids))
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
    product = await _get_or_create_product(session, _inject_uom_id(D.PRODUCT, uom_ids))
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
            "is_initial_step": bool(s.get("is_initial_step", False)),
        }
        step, created = await _get_or_create_step(
            session, route.id, sequence=s["sequence"], **step_kwargs,
        )
        step_by_seq[s["sequence"]] = step
        if created:
            summary["process_segments"] += 1
        in_codes = s.get("input_disposition_codes", [])
        out_codes = s.get("output_disposition_codes", [])
        in_ids = [disp_by_code[c].id for c in in_codes if c in disp_by_code]
        out_ids = [disp_by_code[c].id for c in out_codes if c in disp_by_code]
        await ProductDefService.set_step_input_dispositions(
            session, step.id, in_ids,
        )
        summary["input_disposition_links"] += len(in_ids)
        await ProductDefService.set_step_output_dispositions(
            session, step.id, out_ids,
        )
        summary["output_disposition_links"] += len(out_ids)

    # ── 5. BOM (with process_segment_id links) ─────────────────────────────
    bom, bom_created = await _get_or_create_bom(session, product.id, version="1.0")
    if bom_created:
        for item in D.BOM_ITEMS:
            item_kwargs = {k: v for k, v in _inject_uom_id(item, uom_ids).items() if k != "step_sequence"}
            step_seq = item.get("step_sequence")
            if step_seq and step_seq in step_by_seq:
                item_kwargs["process_segment_id"] = step_by_seq[step_seq].id
            await ProductDefService.create_bom_item(session, bom.id, **item_kwargs)
            summary["bom_items"] += 1
    else:
        # Patch existing BOM items that are missing process_segment_id
        result = await session.execute(
            select(BOMItem).where(BOMItem.bom_id == bom.id, BOMItem.is_active.is_(True))
        )
        existing_items = {bi.material_code: bi for bi in result.scalars().all()}
        for item in D.BOM_ITEMS:
            bi = existing_items.get(item["material_code"])
            step_seq = item.get("step_sequence")
            if bi and step_seq and step_seq in step_by_seq and bi.process_segment_id is None:
                bi.process_segment_id = step_by_seq[step_seq].id

    # ── 6. Transitions: derived from input/output disposition lists ──
    # set when the steps were created above; nothing more to do here.

    # ── 7. Step Parameters ────────────────────────────────────────────
    if route_created:
        for seq, params in D.STEP_PARAMS.items():
            step = step_by_seq[seq]
            for p in params:
                await ProductDefService.create_step_parameter(session, step.id, **_inject_uom_id(p, uom_ids))
                summary["segment_parameters"] += 1

    # ── 8. Data Collection Definitions ────────────────────────────────
    for seq, defs in D.DATA_DEFS.items():
        step = step_by_seq[seq]
        for d in defs:
            dd = _inject_uom_id(d, uom_ids)
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

    # ── 10. Segment Material Requirements (ISA-95 Part 2) ─────────────
    if hasattr(D, "SEGMENT_MATERIAL_REQUIREMENTS"):
        for req in D.SEGMENT_MATERIAL_REQUIREMENTS:
            step = step_by_seq.get(req["step_sequence"])
            mat_id = mat_ids.get(req["material_code"])
            if step is None or mat_id is None:
                continue
            if await _get_or_create_segment_material_requirement(
                session,
                step_id=step.id,
                material_id=mat_id,
                quantity=req["quantity"],
                uom=req["uom"],
                material_use=req["material_use"],
                position=req.get("position", 0),
                description=req.get("description"),
            ):
                summary["segment_material_requirements"] += 1

    # ── 11. OperationsDefinition ↔ Material assignments ───────────────
    if hasattr(D, "ROUTE_MATERIAL_ASSIGNMENTS"):
        for code in D.ROUTE_MATERIAL_ASSIGNMENTS:
            mat_id = mat_ids.get(code)
            if mat_id is None:
                continue
            if await _get_or_create_route_material_assignment(
                session, route_id=route.id, material_id=mat_id,
            ):
                summary["route_material_assignments"] += 1

    await session.commit()
    logger.info("CPG ERP demo data seeded: %s", summary)
    return summary


async def _seed_four_twelves_schedule(session: AsyncSession) -> dict[str, Any]:
    """
    Create the 'four twelves' work schedule if it doesn't already exist.
    Four 12-hour alternating day/night shifts; idempotent.
    """
    SCHED_NAME = "Manufacturing Company - four twelves"
    existing = await session.execute(
        select(_WorkScheduleModel).where(_WorkScheduleModel.name == SCHED_NAME)
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row is not None:
        if not existing_row.is_active:
            # Soft-deleted — reactivate it; its children are still active
            existing_row.is_active = True
            await session.flush()
        return {"work_schedule": 0}

    schedule = await _WorkScheduleSvc.create_schedule(
        session, SCHED_NAME, "Four 12 hour alternating day/night shifts",
    )

    # Day shift: 07:00 for 12 hours
    day_shift = await _WorkScheduleSvc.create_shift(
        session, schedule.id,
        name="Day", description="Day shift",
        start_time=time(7, 0, 0),
        duration_seconds=int(timedelta(hours=12).total_seconds()),
    )
    # Night shift: 19:00 for 12 hours
    night_shift = await _WorkScheduleSvc.create_shift(
        session, schedule.id,
        name="Night", description="Night shift",
        start_time=time(19, 0, 0),
        duration_seconds=int(timedelta(hours=12).total_seconds()),
    )

    # 7 days ON, 7 OFF — day rotation
    day_rotation = await _WorkScheduleSvc.create_rotation(
        session, schedule.id, name="Day", description="Day",
    )
    await _WorkScheduleSvc.add_rotation_segment(
        session, day_rotation.id,
        shift_id=day_shift.id, days_on=7, days_off=7, sequence=1,
    )

    # 7 nights ON, 7 OFF — night rotation
    night_rotation = await _WorkScheduleSvc.create_rotation(
        session, schedule.id, name="Night", description="Night",
    )
    await _WorkScheduleSvc.add_rotation_segment(
        session, night_rotation.id,
        shift_id=night_shift.id, days_on=7, days_off=7, sequence=1,
    )

    rotation_start_ab = date(2014, 1, 2)
    rotation_start_cd = date(2014, 1, 9)
    await _WorkScheduleSvc.create_team(
        session, schedule.id, name="A", description="A day shift",
        rotation_id=day_rotation.id, rotation_start=rotation_start_ab,
    )
    await _WorkScheduleSvc.create_team(
        session, schedule.id, name="B", description="B night shift",
        rotation_id=night_rotation.id, rotation_start=rotation_start_ab,
    )
    await _WorkScheduleSvc.create_team(
        session, schedule.id, name="C", description="C day shift",
        rotation_id=day_rotation.id, rotation_start=rotation_start_cd,
    )
    await _WorkScheduleSvc.create_team(
        session, schedule.id, name="D", description="D night shift",
        rotation_id=night_rotation.id, rotation_start=rotation_start_cd,
    )

    return {"work_schedule": 1}


async def seed_plant_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create the ISA-95 physical hierarchy, assign equipment state models,
    and set up equipment-material assignments.

    Returns a summary dict with counts.
    """
    await _require_erp_seed(
        session,
        scenario="CPG",
        route_name=D.ROUTE_NAME,
        erp_endpoint="/api/v1/demo/seed-cpg-erp",
    )

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
    uom_ids = await _uom_id_map(session)

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
            design_speed_uom_id=uom_ids[em["design_speed_uom"]],
            reject_uom_id=uom_ids[em["reject_uom"]],
            target_oee=em["target_oee"],
        )
        if created:
            summary["equipment_materials"] += 1

    # ── 4b. Equipment Classes (ISA-95 Part 2) ─────────────────────────
    ec_counts = await _seed_equipment_classes(session, D, equip_map)
    summary.update(ec_counts)

    # Reload class_map (codes → ids) — needed for segment linking below
    class_map = await _equipment_class_id_map(session)

    # ── 4c. Back-fill ProcessSegment.equipment_class_id ───────────────
    summary["segment_equipment_class_assignments"] = 0
    if hasattr(D, "STEP_EQUIPMENT_CLASS"):
        summary["segment_equipment_class_assignments"] = (
            await _assign_segment_equipment_classes(
                session,
                route_name=D.ROUTE_NAME,
                step_class_map=D.STEP_EQUIPMENT_CLASS,
                class_id_map=class_map,
            )
        )

    # ── 4d. Segment Equipment Requirements ────────────────────────────
    summary["segment_equipment_requirements"] = 0
    if hasattr(D, "SEGMENT_EQUIPMENT_REQUIREMENTS"):
        step_by_seq = await _segments_by_sequence(session, D.ROUTE_NAME)
        for req in D.SEGMENT_EQUIPMENT_REQUIREMENTS:
            step = step_by_seq.get(req["step_sequence"])
            if step is None:
                continue
            equip_code = req.get("equipment_code")
            class_code = req.get("equipment_class_code")
            equip_id = equip_map.get(equip_code) if equip_code else None
            class_id = class_map.get(class_code) if class_code else None
            if equip_id is None and class_id is None:
                continue
            if await _get_or_create_segment_equipment_requirement(
                session,
                step_id=step.id,
                equipment_id=equip_id,
                equipment_class_id=class_id,
                use_type=req.get("use_type", "preferred"),
                description=req.get("description"),
            ):
                summary["segment_equipment_requirements"] += 1

    # ── 4e. Equipment Capabilities (ISA-95 Part 4) ────────────────────
    summary["equipment_capabilities"] = 0
    if hasattr(D, "EQUIPMENT_CAPABILITIES"):
        prop_lookup = await _equipment_class_property_lookup(session)
        for cap in D.EQUIPMENT_CAPABILITIES:
            equip_id = equip_map.get(cap["equipment_code"])
            class_id = class_map.get(cap["equipment_class_code"])
            if equip_id is None or class_id is None:
                continue
            class_props = prop_lookup.get(cap["equipment_class_code"], {})
            properties: list[dict[str, Any]] = []
            for p in cap.get("properties", []):
                cp_id = class_props.get(p["property_name"])
                if cp_id is not None:
                    properties.append({"class_property_id": cp_id, "value": p["value"]})
            if await _get_or_create_equipment_capability(
                session,
                equipment_id=equip_id,
                equipment_class_id=class_id,
                capability_type=cap.get("capability_type", "available"),
                reason=cap.get("reason"),
                properties=properties,
            ):
                summary["equipment_capabilities"] += 1

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

    # ── 7. Work Schedule ──────────────────────────────────────────────
    ws_counts = await _seed_four_twelves_schedule(session)
    summary.update(ws_counts)

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
                                "process_segments": 0,
                                "input_disposition_links": 0,
                                "output_disposition_links": 0,
                                "segment_parameters": 0, "data_definitions": 0,
                                "quality_tests": 0, "dispositions": 0,
                                "material_lots": 0,
                                "segment_material_requirements": 0,
                                "route_material_assignments": 0}

    # ── 0. Ensure demo-specific UOMs exist (mL, g, mm, °C, ...) ─────
    # Must run BEFORE materials — MaterialDefinition.uom_id has an FK to
    # units_of_measure.id.
    await _ensure_demo_uoms(session)
    uom_ids = await _uom_id_map(session)

    # ── 1. Materials ──────────────────────────────────────────────────
    mat_ids: dict[str, UUID] = {}
    for m in E.MATERIALS:
        mat = await _get_or_create_material(session, _inject_uom_id(m, uom_ids))
        mat_ids[m["code"]] = mat.id
        summary["materials"] += 1

    # ── 1b. Material Lots (initial raw-material inventory) ────────────
    for ml in E.MATERIAL_LOTS:
        mat_id = mat_ids.get(ml["material_code"])
        if mat_id is None:
            continue
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
    product = await _get_or_create_product(session, _inject_uom_id(E.PRODUCT, uom_ids))
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
            "is_initial_step": bool(s.get("is_initial_step", False)),
        }
        step, created = await _get_or_create_step(
            session, route.id, sequence=s["sequence"], **step_kwargs,
        )
        step_by_seq[s["sequence"]] = step
        if created:
            summary["process_segments"] += 1
        in_codes = s.get("input_disposition_codes", [])
        out_codes = s.get("output_disposition_codes", [])
        in_ids = [disp_by_code[c].id for c in in_codes if c in disp_by_code]
        out_ids = [disp_by_code[c].id for c in out_codes if c in disp_by_code]
        await ProductDefService.set_step_input_dispositions(
            session, step.id, in_ids,
        )
        summary["input_disposition_links"] += len(in_ids)
        await ProductDefService.set_step_output_dispositions(
            session, step.id, out_ids,
        )
        summary["output_disposition_links"] += len(out_ids)

    # ── 5. BOM (with process_segment_id links) ─────────────────────────────
    bom, bom_created = await _get_or_create_bom(session, product.id, version="1.0")
    if bom_created:
        for item in E.BOM_ITEMS:
            item_kwargs = {k: v for k, v in _inject_uom_id(item, uom_ids).items() if k != "step_sequence"}
            step_seq = item.get("step_sequence")
            if step_seq and step_seq in step_by_seq:
                item_kwargs["process_segment_id"] = step_by_seq[step_seq].id
            await ProductDefService.create_bom_item(session, bom.id, **item_kwargs)
            summary["bom_items"] += 1
    else:
        # Patch existing BOM items that are missing process_segment_id
        result = await session.execute(
            select(BOMItem).where(BOMItem.bom_id == bom.id, BOMItem.is_active.is_(True))
        )
        existing_items = {bi.material_code: bi for bi in result.scalars().all()}
        for item in E.BOM_ITEMS:
            bi = existing_items.get(item["material_code"])
            step_seq = item.get("step_sequence")
            if bi and step_seq and step_seq in step_by_seq and bi.process_segment_id is None:
                bi.process_segment_id = step_by_seq[step_seq].id

    # ── 6. Transitions: derived from input/output disposition lists ──
    # set when the steps were created above; nothing more to do here.

    # ── 7. Step Parameters ────────────────────────────────────────────
    if route_created:
        for seq, params in E.STEP_PARAMS.items():
            step = step_by_seq[seq]
            for p in params:
                await ProductDefService.create_step_parameter(session, step.id, **_inject_uom_id(p, uom_ids))
                summary["segment_parameters"] += 1

    # ── 8. Data Collection Definitions
    for seq, defs in E.DATA_DEFS.items():
        step = step_by_seq[seq]
        for d in defs:
            dd = _inject_uom_id(d, uom_ids)
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

    # ── 10. Segment Material Requirements (ISA-95 Part 2) ─────────────
    for req in E.SEGMENT_MATERIAL_REQUIREMENTS:
        step = step_by_seq.get(req["step_sequence"])
        mat_id = mat_ids.get(req["material_code"])
        if step is None or mat_id is None:
            continue
        if await _get_or_create_segment_material_requirement(
            session,
            step_id=step.id,
            material_id=mat_id,
            quantity=req["quantity"],
            uom=req["uom"],
            material_use=req["material_use"],
            position=req.get("position", 0),
            description=req.get("description"),
        ):
            summary["segment_material_requirements"] += 1

    # ── 11. OperationsDefinition ↔ Material assignments ───────────────
    for code in E.ROUTE_MATERIAL_ASSIGNMENTS:
        mat_id = mat_ids.get(code)
        if mat_id is None:
            continue
        if await _get_or_create_route_material_assignment(
            session, route_id=route.id, material_id=mat_id,
        ):
            summary["route_material_assignments"] += 1

    await session.commit()
    logger.info("Electronics ERP demo data seeded: %s", summary)
    return summary


async def seed_electronics_plant_data(session: AsyncSession) -> dict[str, Any]:
    """
    Create the ISA-95 physical hierarchy for the Electronics demo.

    Returns a summary dict with counts.
    """
    await _require_erp_seed(
        session,
        scenario="Electronics",
        route_name=E.ROUTE_NAME,
        erp_endpoint="/api/v1/demo/seed-electronics-erp",
    )

    summary: dict[str, Any] = {"sites": 0, "areas": 0,
                                "production_lines": 0, "work_cells": 0,
                                "equipment": 0, "equipment_materials": 0,
                                "segment_equipment_class_assignments": 0,
                                "segment_equipment_requirements": 0,
                                "equipment_capabilities": 0,
                                "storage_locations": 0,
                                "inventory_received": 0}

    uom_ids = await _uom_id_map(session)

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
    uom_ids = await _uom_id_map(session)

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
            design_speed_uom_id=uom_ids[em["design_speed_uom"]],
            reject_uom_id=uom_ids[em["reject_uom"]],
            target_oee=em["target_oee"],
        )
        if created:
            summary["equipment_materials"] += 1

    # ── 4b. Equipment Classes (ISA-95 Part 2) ─────────────────────────
    ec_counts = await _seed_equipment_classes(session, E, equip_map)
    summary.update(ec_counts)

    # Reload class_map (codes → ids) — needed for segment linking below
    class_map = await _equipment_class_id_map(session)

    # ── 4c. Back-fill ProcessSegment.equipment_class_id ───────────────
    # Links each segment to the equipment class that can perform it.
    # Requires ERP data (segments) to already exist.
    if hasattr(E, "STEP_EQUIPMENT_CLASS"):
        summary["segment_equipment_class_assignments"] = (
            await _assign_segment_equipment_classes(
                session,
                route_name=E.ROUTE_NAME,
                step_class_map=E.STEP_EQUIPMENT_CLASS,
                class_id_map=class_map,
            )
        )

    # ── 4d. Segment Equipment Requirements ────────────────────────────
    if hasattr(E, "SEGMENT_EQUIPMENT_REQUIREMENTS"):
        step_by_seq = await _segments_by_sequence(session, E.ROUTE_NAME)
        for req in E.SEGMENT_EQUIPMENT_REQUIREMENTS:
            step = step_by_seq.get(req["step_sequence"])
            if step is None:
                continue
            equip_code = req.get("equipment_code")
            class_code = req.get("equipment_class_code")
            equip_id = equip_map.get(equip_code) if equip_code else None
            class_id = class_map.get(class_code) if class_code else None
            if equip_id is None and class_id is None:
                continue
            if await _get_or_create_segment_equipment_requirement(
                session,
                step_id=step.id,
                equipment_id=equip_id,
                equipment_class_id=class_id,
                use_type=req.get("use_type", "preferred"),
                description=req.get("description"),
            ):
                summary["segment_equipment_requirements"] += 1

    # ── 4e. Equipment Capabilities (ISA-95 Part 4) ────────────────────
    if hasattr(E, "EQUIPMENT_CAPABILITIES"):
        # Build {class_code: {property_name: class_property_id}}
        prop_lookup = await _equipment_class_property_lookup(session)
        for cap in E.EQUIPMENT_CAPABILITIES:
            equip_id = equip_map.get(cap["equipment_code"])
            class_id = class_map.get(cap["equipment_class_code"])
            if equip_id is None or class_id is None:
                continue
            # Resolve property names to class_property_ids
            class_props = prop_lookup.get(cap["equipment_class_code"], {})
            properties: list[dict[str, Any]] = []
            for p in cap.get("properties", []):
                cp_id = class_props.get(p["property_name"])
                if cp_id is not None:
                    properties.append({"class_property_id": cp_id, "value": p["value"]})
            if await _get_or_create_equipment_capability(
                session,
                equipment_id=equip_id,
                equipment_class_id=class_id,
                capability_type=cap.get("capability_type", "available"),
                reason=cap.get("reason"),
                properties=properties,
            ):
                summary["equipment_capabilities"] += 1

    # ── 5. Storage Locations ──────────────────────────────────────────
    loc_map: dict[str, UUID] = {}
    for loc in E.STORAGE_LOCATIONS:
        sl = await _get_or_create_storage_location(
            session, site.id, **loc,
        )
        loc_map[loc["code"]] = sl.id
        summary["storage_locations"] += 1

    # ── 6. Receive material lots into warehouse storage ───────────────
    # Receive → receiving dock, putaway → material-specific warehouse.
    recv_loc_id = loc_map.get("EB-RECV-01")
    if recv_loc_id:
        lot_rows = await _material_lot_list(session)
        for lot in lot_rows:
            mat_code = lot["material_code"]
            storage_code = E.MATERIAL_STORAGE_MAP.get(mat_code)
            if storage_code is None or lot["quantity_on_hand"] <= 0:
                continue
            storage_loc_id = loc_map.get(storage_code)
            if storage_loc_id is None:
                continue
            # Idempotent: skip if already received
            if await _inventory_already_received(session, lot["lot_id"], storage_loc_id):
                continue
            qty = lot["quantity_on_hand"]
            await InventoryTransactionService.receive(
                session,
                material_lot_id=lot["lot_id"],
                to_location_id=recv_loc_id,
                quantity=qty,
                reason="Electronics demo seed — initial goods receipt",
            )
            await InventoryTransactionService.putaway(
                session,
                material_lot_id=lot["lot_id"],
                from_location_id=recv_loc_id,
                to_location_id=storage_loc_id,
                quantity=qty,
                reason="Electronics demo seed — initial putaway",
            )
            summary["inventory_received"] += 1

    # ── 7. Work Schedule ──────────────────────────────────────────────
    ws_counts = await _seed_four_twelves_schedule(session)
    summary.update(ws_counts)

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
    """Return existing work cell by code (re-parenting if needed), or create."""
    result = await session.execute(
        select(WorkCell).where(WorkCell.code == kwargs["code"], WorkCell.is_active.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Re-attach orphan rows from prior seed runs that pointed at a
        # different line — otherwise the tree views (filtered by line_id)
        # silently hide this work cell.
        if existing.line_id != line_id:
            existing.line_id = line_id
            await session.flush()
        return existing
    return await PhysicalModelService.create_work_cell(session, line_id, **kwargs)


async def _get_or_create_equipment(session: AsyncSession, wc_id: UUID, **kwargs: Any) -> Any:
    """Return existing equipment by code (re-parenting if needed), or create."""
    result = await session.execute(
        select(Equipment).where(Equipment.code == kwargs["code"], Equipment.is_active.is_(True))
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.work_cell_id != wc_id:
            existing.work_cell_id = wc_id
            await session.flush()
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


async def _uom_id_map(session: AsyncSession) -> dict[str, UUID]:
    """Return {symbol: id} for all units_of_measure rows."""
    result = await session.execute(
        select(UnitOfMeasure.symbol, UnitOfMeasure.id)
    )
    return {row[0]: row[1] for row in result.all()}


def _inject_uom_id(d: dict, uom_ids: dict[str, UUID]) -> dict:
    """Return a copy of *d* with the 'uom' key replaced by 'uom_id' (UUID or None)."""
    out = dict(d)
    if "uom" in out:
        sym = out.pop("uom")
        out["uom_id"] = uom_ids[sym] if sym is not None else None
    return out


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
    ("RPM",    "revolutions per minute", "rate",        1.0 / 60, 0.0),
    ("bottle/min", "bottles per minute", "rate",        1.0, 0.0),
    ("label/min",  "labels per minute",  "rate",        1.0, 0.0),
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
        # Ensure demo-specific UoMs (cph, RPM, bottle/min, ...) exist. This
        # is idempotent and makes the function self-sufficient when called
        # outside the ERP seed path.
        await _ensure_demo_uoms(session)
        # Build a UoM symbol → id lookup so seed data can use human-readable
        # symbols (e.g. "L", "s"). The DB column stores the UUID.
        uom_rows = await session.execute(
            select(UnitOfMeasure.symbol, UnitOfMeasure.id)
        )
        uom_symbol_to_id: dict[str, UUID] = {sym: uid for sym, uid in uom_rows.all()}

        for prop_data in data_module.EQUIPMENT_CLASS_PROPERTIES:
            pdata = dict(prop_data)
            class_code = pdata.pop("class_code")
            class_id = class_map[class_code]
            # Translate UoM symbol → id if seed data provided a symbol string
            uom_val = pdata.get("uom_id")
            if isinstance(uom_val, str):
                uom_id = uom_symbol_to_id.get(uom_val)
                if uom_id is None:
                    raise ValueError(
                        f"Unknown UoM symbol '{uom_val}' for equipment class "
                        f"property {class_code}.{pdata.get('name')}. "
                        "Add it to _DEMO_UOMS or the built-in UoM seed."
                    )
                pdata["uom_id"] = uom_id
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


# ---------------------------------------------------------------------------
# ISA-95 Part 2: helpers for segment/equipment linking and capabilities
# ---------------------------------------------------------------------------

async def _equipment_class_id_map(session: AsyncSession) -> dict[str, UUID]:
    """Return {equipment_class.code: id} for all classes in the DB."""
    result = await session.execute(
        select(EquipmentClass.code, EquipmentClass.id)
    )
    return {code: cid for code, cid in result.all()}


async def _equipment_class_property_lookup(
    session: AsyncSession,
) -> dict[str, dict[str, UUID]]:
    """Return {class_code: {property_name: class_property_id}} for all classes."""
    result = await session.execute(
        select(
            EquipmentClass.code,
            EquipmentClassProperty.name,
            EquipmentClassProperty.id,
        ).join(
            EquipmentClassProperty,
            EquipmentClassProperty.equipment_class_id == EquipmentClass.id,
        )
    )
    lookup: dict[str, dict[str, UUID]] = {}
    for class_code, prop_name, prop_id in result.all():
        lookup.setdefault(class_code, {})[prop_name] = prop_id
    return lookup


async def _segments_by_sequence(
    session: AsyncSession, route_name: str,
) -> dict[int, ProcessSegment]:
    """Return {sequence: ProcessSegment} for all segments of the named route."""
    result = await session.execute(
        select(ProcessSegment)
        .join(OperationsDefinition,
              OperationsDefinition.id == ProcessSegment.route_id)
        .where(OperationsDefinition.name == route_name)
    )
    segs = result.scalars().all()
    return {s.sequence: s for s in segs}


async def _assign_segment_equipment_classes(
    session: AsyncSession,
    route_name: str,
    step_class_map: dict[int, str],
    class_id_map: dict[str, UUID],
) -> int:
    """Back-fill ProcessSegment.equipment_class_id for each (seq, class_code)."""
    segs = await _segments_by_sequence(session, route_name)
    changed = 0
    for seq, class_code in step_class_map.items():
        seg = segs.get(seq)
        class_id = class_id_map.get(class_code)
        if seg is None or class_id is None:
            continue
        if seg.equipment_class_id != class_id:
            seg.equipment_class_id = class_id
            changed += 1
    if changed:
        await session.flush()
    return changed


async def _get_or_create_segment_equipment_requirement(
    session: AsyncSession,
    *,
    step_id: UUID,
    equipment_id: UUID | None = None,
    equipment_class_id: UUID | None = None,
    use_type: str = "preferred",
    description: str | None = None,
) -> bool:
    """Create a SegmentEquipmentRequirement unless one already exists.

    Exactly one of ``equipment_id`` or ``equipment_class_id`` must be set
    (ISA-95 Part 2 EquipmentSegmentSpecification; enforced at the DB by
    ``ck_segment_equip_req_one_target``).  Dedup key is
    (step_id, target, use_type).
    """
    from mes.core.product_def.models import SegmentEquipmentRequirement

    if (equipment_id is None) == (equipment_class_id is None):
        raise ValueError(
            "Exactly one of equipment_id or equipment_class_id must be set."
        )

    stmt = select(SegmentEquipmentRequirement).where(
        SegmentEquipmentRequirement.step_id == step_id,
        SegmentEquipmentRequirement.use_type == use_type,
    )
    if equipment_id is not None:
        stmt = stmt.where(SegmentEquipmentRequirement.equipment_id == equipment_id)
    else:
        stmt = stmt.where(
            SegmentEquipmentRequirement.equipment_class_id == equipment_class_id
        )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        return False

    await ProductDefService.create_step_equipment_requirement(
        session,
        step_id=step_id,
        equipment_id=equipment_id,
        equipment_class_id=equipment_class_id,
        use_type=use_type,
        description=description,
    )
    return True


async def _get_or_create_segment_material_requirement(
    session: AsyncSession,
    *,
    step_id: UUID,
    material_id: UUID,
    quantity: float,
    uom: str,
    material_use: str,
    position: int = 0,
    description: str | None = None,
) -> bool:
    """Create a SegmentMaterialRequirement unless one already exists for
    (step_id, material_id, material_use).  Returns True if created."""
    from mes.core.product_def.models import SegmentMaterialRequirement

    result = await session.execute(
        select(SegmentMaterialRequirement).where(
            SegmentMaterialRequirement.step_id == step_id,
            SegmentMaterialRequirement.material_id == material_id,
            SegmentMaterialRequirement.material_use == material_use,
        )
    )
    if result.scalar_one_or_none() is not None:
        return False

    await ProductDefService.create_step_material_requirement(
        session,
        step_id=step_id,
        material_id=material_id,
        quantity=quantity,
        uom=uom,
        material_use=material_use,
        position=position,
        description=description,
    )
    return True


async def _get_or_create_route_material_assignment(
    session: AsyncSession,
    *,
    route_id: UUID,
    material_id: UUID,
) -> bool:
    """Assign a material to the OperationsDefinition unless already assigned.
    Returns True if a new assignment was created."""
    from mes.core.product_def.models import OperationsDefinitionMaterialAssignment

    result = await session.execute(
        select(OperationsDefinitionMaterialAssignment).where(
            OperationsDefinitionMaterialAssignment.route_id == route_id,
            OperationsDefinitionMaterialAssignment.material_id == material_id,
            OperationsDefinitionMaterialAssignment.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none() is not None:
        return False

    await ProductDefService.assign_material_to_route(
        session, route_id, material_id,
    )
    return True


async def _get_or_create_equipment_capability(
    session: AsyncSession,
    *,
    equipment_id: UUID,
    equipment_class_id: UUID,
    capability_type: str = "available",
    reason: str | None = None,
    properties: list[dict[str, Any]] | None = None,
) -> bool:
    """Create an EquipmentCapability unless one already exists for
    (equipment_id, equipment_class_id, capability_type).  Returns True if
    created."""
    result = await session.execute(
        select(EquipmentCapability)
        .where(
            EquipmentCapability.equipment_id == equipment_id,
            EquipmentCapability.equipment_class_id == equipment_class_id,
            EquipmentCapability.capability_type == capability_type,
        )
        .limit(1)
    )
    if result.scalars().first() is not None:
        return False

    await PhysicalModelService.create_capability(
        session,
        equip_id=equipment_id,
        equipment_class_id=equipment_class_id,
        capability_type=capability_type,
        reason=reason,
        properties=properties or [],
    )
    return True
