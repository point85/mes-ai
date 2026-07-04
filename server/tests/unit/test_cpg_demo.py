"""
Unit tests for the CPG Demo seed module.

Tests cover:
  - cpg_data constants completeness
  - service module imports
  - route registration in main.py
  - data relationships (transitions reference valid step sequences, etc.)
"""

from __future__ import annotations

import importlib

import pytest


# ═════════════════════════════════════════════════════════════════════
# 1. DATA CONSTANTS — cpg_data.py
# ═════════════════════════════════════════════════════════════════════


class TestCPGDataMaterials:
    """Verify material definitions are complete and consistent."""

    def test_material_count(self):
        from mes.core.demo.cpg_data import MATERIALS
        assert len(MATERIALS) == 11

    def test_all_materials_have_required_fields(self):
        from mes.core.demo.cpg_data import MATERIALS
        for m in MATERIALS:
            assert "code" in m
            assert "name" in m
            assert "material_type" in m
            assert "uom" in m

    def test_material_codes_unique(self):
        from mes.core.demo.cpg_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert len(codes) == len(set(codes))

    def test_material_types_valid(self):
        from mes.core.demo.cpg_data import MATERIALS
        valid_types = {"raw", "semi", "finished", "packaging"}
        for m in MATERIALS:
            assert m["material_type"] in valid_types, f"{m['code']} has invalid type"

    def test_finished_product_present(self):
        from mes.core.demo.cpg_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert "FG-OJ-1L" in codes


class TestCPGDataProduct:
    """Verify product definition."""

    def test_product_code_matches_finished_material(self):
        from mes.core.demo.cpg_data import PRODUCT
        assert PRODUCT["code"] == "FG-OJ-1L"

    def test_product_type_is_process(self):
        from mes.core.demo.cpg_data import PRODUCT
        assert PRODUCT["product_type"] == "process"


class TestCPGDataBOM:
    """Verify BOM items."""

    def test_bom_item_count(self):
        from mes.core.demo.cpg_data import BOM_ITEMS
        assert len(BOM_ITEMS) == 9

    def test_bom_positions_unique(self):
        from mes.core.demo.cpg_data import BOM_ITEMS
        positions = [i["position"] for i in BOM_ITEMS]
        assert len(positions) == len(set(positions))

    def test_bom_quantities_positive(self):
        from mes.core.demo.cpg_data import BOM_ITEMS
        for item in BOM_ITEMS:
            assert item["quantity"] > 0, f"{item['material_code']} qty <= 0"

    def test_bom_materials_exist_in_materials_list(self):
        from mes.core.demo.cpg_data import BOM_ITEMS, MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for item in BOM_ITEMS:
            assert item["material_code"] in mat_codes, (
                f"BOM item {item['material_code']} not in MATERIALS"
            )


class TestCPGDataRoute:
    """Verify route steps and transitions."""

    def test_step_count(self):
        from mes.core.demo.cpg_data import STEPS
        assert len(STEPS) == 7  # 5 production + 1 rework + 1 mrb

    def test_step_sequences_unique(self):
        from mes.core.demo.cpg_data import STEPS
        seqs = [s["sequence"] for s in STEPS]
        assert len(seqs) == len(set(seqs))

    def test_step_types_valid(self):
        from mes.core.demo.cpg_data import STEPS
        valid = {"production", "inspection", "rework", "mrb"}
        for s in STEPS:
            assert s["step_type"] in valid, f"Step {s['sequence']} invalid type"

    def test_rework_step_present(self):
        from mes.core.demo.cpg_data import STEPS
        rework = [s for s in STEPS if s["step_type"] == "rework"]
        assert len(rework) == 1

    def test_mrb_step_present(self):
        from mes.core.demo.cpg_data import STEPS
        mrb = [s for s in STEPS if s["step_type"] == "mrb"]
        assert len(mrb) == 1

    def test_production_steps_count(self):
        from mes.core.demo.cpg_data import STEPS
        prod = [s for s in STEPS if s["step_type"] == "production"]
        assert len(prod) == 4

    def test_inspection_step_count(self):
        from mes.core.demo.cpg_data import STEPS
        insp = [s for s in STEPS if s["step_type"] == "inspection"]
        assert len(insp) == 1


class TestCPGDataTransitions:
    """Verify per-step input/output disposition lists form a valid graph."""

    def test_dispositions_have_unique_codes(self):
        from mes.core.demo.cpg_data import DISPOSITIONS
        codes = [d["code"] for d in DISPOSITIONS]
        assert len(codes) == len(set(codes))

    def test_step_disposition_codes_reference_catalog(self):
        from mes.core.demo.cpg_data import STEPS, DISPOSITIONS
        catalog = {d["code"] for d in DISPOSITIONS}
        for s in STEPS:
            for c in s.get("input_disposition_codes", []):
                assert c in catalog, f"Step {s['sequence']} input '{c}' not in catalog"
            for c in s.get("output_disposition_codes", []):
                assert c in catalog, f"Step {s['sequence']} output '{c}' not in catalog"

    def test_exactly_one_initial_step(self):
        from mes.core.demo.cpg_data import STEPS
        initials = [s for s in STEPS if s.get("is_initial_step")]
        assert len(initials) == 1

    def test_at_least_one_terminal_step(self):
        from mes.core.demo.cpg_data import STEPS
        terminals = [s for s in STEPS if not s.get("output_disposition_codes")]
        assert len(terminals) >= 1

    def test_qc_step_has_pass_and_fail_outputs(self):
        """Step 30 (QC) should expose pass/fail/escalate disposition outputs."""
        from mes.core.demo.cpg_data import STEPS
        qc = next(s for s in STEPS if s["sequence"] == 30)
        outs = set(qc.get("output_disposition_codes", []))
        assert "QC-PASS" in outs
        assert "QC-FAIL" in outs

    def test_rework_loops_back_via_disposition(self):
        """Re-Blend (60) must emit a disposition that some upstream step accepts."""
        from mes.core.demo.cpg_data import STEPS
        rb = next(s for s in STEPS if s["sequence"] == 60)
        outs = set(rb.get("output_disposition_codes", []))
        # Build set of all input codes across all steps
        all_inputs = set()
        for s in STEPS:
            all_inputs.update(s.get("input_disposition_codes", []))
        assert outs & all_inputs, "Re-Blend output dispositions don't feed any step"

    def test_mrb_has_multiple_dispositions(self):
        """MRB step (70) should offer 2+ output dispositions."""
        from mes.core.demo.cpg_data import STEPS
        mrb = next(s for s in STEPS if s["sequence"] == 70)
        assert len(mrb.get("output_disposition_codes", [])) >= 2


class TestCPGDataStepParams:
    """Verify step parameter definitions."""

    def test_all_steps_have_params(self):
        from mes.core.demo.cpg_data import STEP_PARAMS, STEPS
        for s in STEPS:
            assert s["sequence"] in STEP_PARAMS, (
                f"Step {s['sequence']} ({s['name']}) has no parameters"
            )

    def test_param_data_types_valid(self):
        from mes.core.demo.cpg_data import STEP_PARAMS
        valid = {"numeric", "string", "boolean", "enum"}
        for seq, params in STEP_PARAMS.items():
            for p in params:
                assert p["data_type"] in valid, (
                    f"Step {seq} param {p['name']} invalid data_type"
                )

    def test_total_param_count(self):
        from mes.core.demo.cpg_data import STEP_PARAMS
        total = sum(len(params) for params in STEP_PARAMS.values())
        assert total == 21


class TestCPGDataDataDefs:
    """Verify data collection definitions."""

    def test_all_steps_have_data_defs(self):
        from mes.core.demo.cpg_data import DATA_DEFS, STEPS
        for s in STEPS:
            assert s["sequence"] in DATA_DEFS, (
                f"Step {s['sequence']} ({s['name']}) has no data definitions"
            )

    def test_data_def_codes_unique(self):
        from mes.core.demo.cpg_data import DATA_DEFS
        all_codes = []
        for defs in DATA_DEFS.values():
            for d in defs:
                all_codes.append(d["code"])
        assert len(all_codes) == len(set(all_codes))

    def test_data_def_sources_valid(self):
        from mes.core.demo.cpg_data import DATA_DEFS
        valid = {"manual", "equipment", "sensor"}
        for seq, defs in DATA_DEFS.items():
            for d in defs:
                assert d["source"] in valid, (
                    f"Step {seq} data def {d['code']} invalid source"
                )

    def test_total_data_def_count(self):
        from mes.core.demo.cpg_data import DATA_DEFS
        total = sum(len(defs) for defs in DATA_DEFS.values())
        assert total == 21


class TestCPGDataQualityTest:
    """Verify quality test definition."""

    def test_quality_test_is_inline(self):
        from mes.core.demo.cpg_data import QUALITY_TEST
        assert QUALITY_TEST["test_type"] == "inline"

    def test_quality_test_has_code(self):
        from mes.core.demo.cpg_data import QUALITY_TEST
        assert QUALITY_TEST["code"] == "CPG-QC-INLINE"


class TestCPGDataOrders:
    """Verify production orders list is empty (orders created via CRUD)."""

    def test_orders_empty(self):
        from mes.core.demo.cpg_data import ORDERS
        assert ORDERS == []


# ═════════════════════════════════════════════════════════════════════
# 2. PHYSICAL MODEL DATA
# ═════════════════════════════════════════════════════════════════════


class TestCPGDataPhysicalModel:
    """Verify ISA-95 hierarchy data."""

    def test_site_code(self):
        from mes.core.demo.cpg_data import SITE
        assert SITE["code"] == "SB-PLANT"

    def test_area_code(self):
        from mes.core.demo.cpg_data import AREA
        assert AREA["code"] == "SB-JUICE"

    def test_line_code(self):
        from mes.core.demo.cpg_data import LINE
        assert LINE["code"] == "SB-LINE-01"

    def test_work_cell_count(self):
        from mes.core.demo.cpg_data import WORK_CELLS
        assert len(WORK_CELLS) == 6

    def test_work_cell_codes_unique(self):
        from mes.core.demo.cpg_data import WORK_CELLS
        codes = [wc["code"] for wc in WORK_CELLS]
        assert len(codes) == len(set(codes))

    def test_work_cell_types_valid(self):
        from mes.core.demo.cpg_data import WORK_CELLS
        for wc in WORK_CELLS:
            assert "code" in wc
            assert "name" in wc

    def test_equipment_count(self):
        from mes.core.demo.cpg_data import EQUIPMENT
        assert len(EQUIPMENT) == 7

    def test_equipment_codes_unique(self):
        from mes.core.demo.cpg_data import EQUIPMENT
        codes = [e["code"] for e in EQUIPMENT]
        assert len(codes) == len(set(codes))

    def test_equipment_reference_valid_work_cells(self):
        from mes.core.demo.cpg_data import EQUIPMENT, WORK_CELLS
        wc_codes = {wc["code"] for wc in WORK_CELLS}
        for e in EQUIPMENT:
            assert e["work_cell_code"] in wc_codes, (
                f"Equipment {e['code']} references invalid WC {e['work_cell_code']}"
            )

    def test_state_models_valid(self):
        from mes.core.demo.cpg_data import EQUIPMENT
        valid = {"packml", "semi_e10"}
        for e in EQUIPMENT:
            assert e["state_model"] in valid, (
                f"Equipment {e['code']} has invalid state model {e['state_model']}"
            )

    def test_two_fillers_in_fill_station(self):
        """WC-FILL should have two fillers for dispatch demo."""
        from mes.core.demo.cpg_data import EQUIPMENT
        fillers = [e for e in EQUIPMENT if e["work_cell_code"] == "WC-FILL"]
        assert len(fillers) == 2

    def test_steps_reference_valid_work_cells(self):
        from mes.core.demo.cpg_data import STEPS, WORK_CELLS
        wc_codes = {wc["code"] for wc in WORK_CELLS}
        for s in STEPS:
            wc = s.get("work_cell_code")
            if wc:
                assert wc in wc_codes, (
                    f"Step {s['sequence']} references invalid WC {wc}"
                )


class TestCPGDataEquipmentMaterials:
    """Verify equipment-material assignments."""

    def test_assignment_count(self):
        from mes.core.demo.cpg_data import EQUIPMENT_MATERIALS
        assert len(EQUIPMENT_MATERIALS) == 7  # one per equipment

    def test_all_equipment_has_assignment(self):
        from mes.core.demo.cpg_data import EQUIPMENT, EQUIPMENT_MATERIALS
        equip_codes = {e["code"] for e in EQUIPMENT}
        assigned_codes = {em["equipment_code"] for em in EQUIPMENT_MATERIALS}
        assert equip_codes == assigned_codes

    def test_target_oee_range(self):
        from mes.core.demo.cpg_data import EQUIPMENT_MATERIALS
        for em in EQUIPMENT_MATERIALS:
            assert 0 < em["target_oee"] <= 100

    def test_design_speeds_positive(self):
        from mes.core.demo.cpg_data import EQUIPMENT_MATERIALS
        for em in EQUIPMENT_MATERIALS:
            assert em["design_speed"] > 0


# ═════════════════════════════════════════════════════════════════════
# 3. SERVICE MODULE IMPORTS
# ═════════════════════════════════════════════════════════════════════


class TestCPGServiceImports:
    """Verify service module is importable."""

    def test_seed_erp_data_importable(self):
        from mes.core.demo.service import seed_erp_data
        assert callable(seed_erp_data)

    def test_seed_plant_data_importable(self):
        from mes.core.demo.service import seed_plant_data
        assert callable(seed_plant_data)


# ═════════════════════════════════════════════════════════════════════
# 4. ROUTE REGISTRATION IN MAIN APP
# ═════════════════════════════════════════════════════════════════════


class TestCPGDemoRouteRegistration:
    """Verify demo router is registered in main.py."""

    def test_demo_router_imported(self):
        from mes.core.demo.routes import router
        assert router is not None
        assert router.prefix == "/api/v1/demo"

    def test_demo_routes_have_two_endpoints(self):
        from mes.core.demo.routes import router
        paths = [r.path for r in router.routes]
        assert any("seed-cpg-erp" in p for p in paths)
        assert any("seed-cpg-plant" in p for p in paths)

    def test_main_app_includes_demo_router(self):
        from mes.main import create_app
        app = create_app()
        route_paths = [r.path for r in app.routes]
        assert "/api/v1/demo/seed-cpg-erp" in route_paths
        assert "/api/v1/demo/seed-cpg-plant" in route_paths


# ═════════════════════════════════════════════════════════════════════
# 5. DATA INTEGRITY — cross-references
# ═════════════════════════════════════════════════════════════════════


class TestCPGDataIntegrity:
    """Cross-reference integrity between data sections."""

    def test_data_def_count_matches_param_count(self):
        """Each step parameter should have a corresponding data definition."""
        from mes.core.demo.cpg_data import STEP_PARAMS, DATA_DEFS
        for seq in STEP_PARAMS:
            assert len(STEP_PARAMS[seq]) == len(DATA_DEFS[seq]), (
                f"Step {seq}: param count ({len(STEP_PARAMS[seq])}) != "
                f"data def count ({len(DATA_DEFS[seq])})"
            )

    def test_route_graph_reachability(self):
        """Every step should be reachable from the initial step via disposition edges."""
        from mes.core.demo.cpg_data import STEPS
        seqs = {s["sequence"] for s in STEPS}
        # Build edges: out_disp_code -> step that lists it as input
        input_owner: dict[str, int] = {}
        for s in STEPS:
            for c in s.get("input_disposition_codes", []):
                input_owner[c] = s["sequence"]
        initial = next(s for s in STEPS if s.get("is_initial_step"))
        reachable: set[int] = set()
        queue = [initial["sequence"]]
        by_seq = {s["sequence"]: s for s in STEPS}
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for c in by_seq[current].get("output_disposition_codes", []):
                nxt = input_owner.get(c)
                if nxt is not None and nxt not in reachable:
                    queue.append(nxt)
        assert seqs == reachable, f"Unreachable steps: {seqs - reachable}"

    def test_equipment_materials_reference_valid_equipment(self):
        from mes.core.demo.cpg_data import EQUIPMENT, EQUIPMENT_MATERIALS
        eq_codes = {e["code"] for e in EQUIPMENT}
        for em in EQUIPMENT_MATERIALS:
            assert em["equipment_code"] in eq_codes

    def test_equipment_materials_reference_valid_material(self):
        from mes.core.demo.cpg_data import MATERIALS, EQUIPMENT_MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for em in EQUIPMENT_MATERIALS:
            assert em["material_code"] in mat_codes
