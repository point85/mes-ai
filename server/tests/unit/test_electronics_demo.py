"""
Unit tests for the Electronics Demo seed module.

Tests cover:
  - electronics_data constants completeness
  - service module imports
  - route registration
  - data relationships (transitions reference valid step sequences, etc.)
"""

from __future__ import annotations

import importlib

import pytest


# ═════════════════════════════════════════════════════════════════════
# 1. DATA CONSTANTS — electronics_data.py
# ═════════════════════════════════════════════════════════════════════


class TestElecDataMaterials:
    """Verify material definitions are complete and consistent."""

    def test_material_count(self):
        from mes.core.demo.electronics_data import MATERIALS
        assert len(MATERIALS) == 9

    def test_all_materials_have_required_fields(self):
        from mes.core.demo.electronics_data import MATERIALS
        for m in MATERIALS:
            assert "code" in m
            assert "name" in m
            assert "material_type" in m
            assert "uom" in m

    def test_material_codes_unique(self):
        from mes.core.demo.electronics_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert len(codes) == len(set(codes))

    def test_material_types_valid(self):
        from mes.core.demo.electronics_data import MATERIALS
        valid_types = {"raw", "semi_finished", "finished", "packaging"}
        for m in MATERIALS:
            assert m["material_type"] in valid_types, f"{m['code']} has invalid type"

    def test_finished_product_present(self):
        from mes.core.demo.electronics_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert "FG-ECB-100" in codes


class TestElecDataProduct:
    """Verify product definition."""

    def test_product_code_matches_finished_material(self):
        from mes.core.demo.electronics_data import PRODUCT
        assert PRODUCT["code"] == "FG-ECB-100"

    def test_product_type_is_discrete(self):
        from mes.core.demo.electronics_data import PRODUCT
        assert PRODUCT["product_type"] == "discrete"


class TestElecDataBOM:
    """Verify bill of material."""

    def test_bom_item_count(self):
        from mes.core.demo.electronics_data import BOM_ITEMS
        assert len(BOM_ITEMS) == 8

    def test_bom_materials_exist(self):
        from mes.core.demo.electronics_data import BOM_ITEMS, MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for item in BOM_ITEMS:
            assert item["material_code"] in mat_codes, f"BOM ref {item['material_code']} not defined"

    def test_bom_positions_unique(self):
        from mes.core.demo.electronics_data import BOM_ITEMS
        positions = [item["position"] for item in BOM_ITEMS]
        assert len(positions) == len(set(positions))

    def test_all_bom_items_have_quantity(self):
        from mes.core.demo.electronics_data import BOM_ITEMS
        for item in BOM_ITEMS:
            assert item["quantity"] > 0


class TestElecDataRoute:
    """Verify route steps."""

    def test_step_count(self):
        from mes.core.demo.electronics_data import STEPS
        assert len(STEPS) == 8

    def test_sequences_unique(self):
        from mes.core.demo.electronics_data import STEPS
        seqs = [s["sequence"] for s in STEPS]
        assert len(seqs) == len(set(seqs))

    def test_sequences_ascending(self):
        from mes.core.demo.electronics_data import STEPS
        seqs = [s["sequence"] for s in STEPS]
        assert seqs == sorted(seqs)

    def test_step_types_valid(self):
        from mes.core.demo.electronics_data import STEPS
        valid = {"production", "inspection", "rework", "mrb"}
        for s in STEPS:
            assert s["step_type"] in valid, f"Step {s['sequence']} has invalid type"

    def test_rework_step_present(self):
        from mes.core.demo.electronics_data import STEPS
        rework = [s for s in STEPS if s["step_type"] == "rework"]
        assert len(rework) >= 1

    def test_mrb_step_present(self):
        from mes.core.demo.electronics_data import STEPS
        mrb = [s for s in STEPS if s["step_type"] == "mrb"]
        assert len(mrb) >= 1

    def test_all_steps_have_cycle_time(self):
        from mes.core.demo.electronics_data import STEPS
        for s in STEPS:
            assert s["expected_cycle_time_sec"] > 0

    def test_all_steps_have_erp_op_number(self):
        from mes.core.demo.electronics_data import STEPS
        for s in STEPS:
            assert s["erp_operation_number"] is not None


class TestElecDataTransitions:
    """Verify step transitions form valid graph."""

    def test_transition_count(self):
        from mes.core.demo.electronics_data import TRANSITIONS
        assert len(TRANSITIONS) == 12

    def test_all_transitions_reference_valid_steps(self):
        from mes.core.demo.electronics_data import TRANSITIONS, STEPS
        valid_seqs = {s["sequence"] for s in STEPS}
        for t in TRANSITIONS:
            assert t["from_seq"] in valid_seqs, f"from_seq {t['from_seq']} not in steps"
            assert t["to_seq"] in valid_seqs, f"to_seq {t['to_seq']} not in steps"

    def test_conditions_valid(self):
        from mes.core.demo.electronics_data import TRANSITIONS
        valid = {"always", "on_pass", "on_fail", "on_rework", "disposition"}
        for t in TRANSITIONS:
            assert t["condition"] in valid, f"Invalid condition: {t['condition']}"

    def test_rework_loop_exists(self):
        """Rework (70) → AOI (40) creates rework loop."""
        from mes.core.demo.electronics_data import TRANSITIONS
        rework_back = [t for t in TRANSITIONS if t["from_seq"] == 70 and t["to_seq"] == 40]
        assert len(rework_back) == 1

    def test_mrb_disposition_exists(self):
        """MRB (80) has disposition transitions."""
        from mes.core.demo.electronics_data import TRANSITIONS
        mrb_disp = [t for t in TRANSITIONS if t["from_seq"] == 80 and t["condition"] == "disposition"]
        assert len(mrb_disp) >= 1

    def test_aoi_branches_to_pass_fail_rework(self):
        """AOI (40) has on_pass, on_fail, and on_rework transitions."""
        from mes.core.demo.electronics_data import TRANSITIONS
        aoi_out = [t for t in TRANSITIONS if t["from_seq"] == 40]
        conditions = {t["condition"] for t in aoi_out}
        assert "on_pass" in conditions
        assert "on_fail" in conditions
        assert "on_rework" in conditions


class TestElecDataStepParams:
    """Verify step parameter definitions."""

    def test_params_defined_for_all_steps(self):
        from mes.core.demo.electronics_data import STEP_PARAMS, STEPS
        step_seqs = {s["sequence"] for s in STEPS}
        assert set(STEP_PARAMS.keys()) == step_seqs

    def test_total_param_count(self):
        from mes.core.demo.electronics_data import STEP_PARAMS
        total = sum(len(params) for params in STEP_PARAMS.values())
        assert total == 26

    def test_param_data_types_valid(self):
        from mes.core.demo.electronics_data import STEP_PARAMS
        valid = {"numeric", "boolean", "string", "enum"}
        for seq, params in STEP_PARAMS.items():
            for p in params:
                assert p["data_type"] in valid, (
                    f"Step {seq} param {p['name']} invalid data_type"
                )


class TestElecDataDataDefs:
    """Verify data collection definitions."""

    def test_defs_defined_for_all_steps(self):
        from mes.core.demo.electronics_data import DATA_DEFS, STEPS
        step_seqs = {s["sequence"] for s in STEPS}
        assert set(DATA_DEFS.keys()) == step_seqs

    def test_total_data_def_count(self):
        from mes.core.demo.electronics_data import DATA_DEFS
        total = sum(len(defs) for defs in DATA_DEFS.values())
        assert total == 28

    def test_data_def_codes_unique(self):
        from mes.core.demo.electronics_data import DATA_DEFS
        codes = []
        for defs in DATA_DEFS.values():
            for d in defs:
                codes.append(d["code"])
        assert len(codes) == len(set(codes))

    def test_data_def_codes_start_with_ecb(self):
        from mes.core.demo.electronics_data import DATA_DEFS
        for defs in DATA_DEFS.values():
            for d in defs:
                assert d["code"].startswith("ECB-"), f"Code {d['code']} missing ECB- prefix"


class TestElecDataQualityTest:
    """Verify quality test definition."""

    def test_quality_test_code(self):
        from mes.core.demo.electronics_data import QUALITY_TEST
        assert QUALITY_TEST["code"] == "ECB-FCT-BOARD"

    def test_quality_test_type_inline(self):
        from mes.core.demo.electronics_data import QUALITY_TEST
        assert QUALITY_TEST["test_type"] == "inline"


class TestElecDataOrders:
    """Verify production orders list is empty (orders created via CRUD)."""

    def test_orders_empty(self):
        from mes.core.demo.electronics_data import ORDERS
        assert ORDERS == []

    def test_serial_template_defined(self):
        from mes.core.demo.electronics_data import SERIAL_TEMPLATE
        assert "{order}" in SERIAL_TEMPLATE
        assert "{seq" in SERIAL_TEMPLATE


class TestElecDataPhysicalModel:
    """Verify ISA-95 physical hierarchy."""

    def test_site_defined(self):
        from mes.core.demo.electronics_data import SITE
        assert SITE["code"] == "APEX-ELEC"

    def test_area_defined(self):
        from mes.core.demo.electronics_data import AREA
        assert AREA["code"] == "PCBA-AREA"

    def test_line_defined(self):
        from mes.core.demo.electronics_data import LINE
        assert LINE["code"] == "LINE-SMT-01"

    def test_work_cell_count(self):
        from mes.core.demo.electronics_data import WORK_CELLS
        assert len(WORK_CELLS) == 7

    def test_work_cell_codes_unique(self):
        from mes.core.demo.electronics_data import WORK_CELLS
        codes = [wc["code"] for wc in WORK_CELLS]
        assert len(codes) == len(set(codes))

    def test_equipment_count(self):
        from mes.core.demo.electronics_data import EQUIPMENT
        assert len(EQUIPMENT) == 8

    def test_equipment_codes_unique(self):
        from mes.core.demo.electronics_data import EQUIPMENT
        codes = [eq["code"] for eq in EQUIPMENT]
        assert len(codes) == len(set(codes))

    def test_equipment_references_valid_work_cells(self):
        from mes.core.demo.electronics_data import EQUIPMENT, WORK_CELLS
        wc_codes = {wc["code"] for wc in WORK_CELLS}
        for eq in EQUIPMENT:
            assert eq["work_cell_code"] in wc_codes, f"Equipment {eq['code']} refs invalid WC"

    def test_dual_pick_and_place(self):
        """Two pick-and-place machines for dispatch demo."""
        from mes.core.demo.electronics_data import EQUIPMENT
        pnp = [eq for eq in EQUIPMENT if eq["code"].startswith("PNP-")]
        assert len(pnp) == 2

    def test_all_equipment_have_state_model(self):
        from mes.core.demo.electronics_data import EQUIPMENT
        valid_models = {"packml", "semi_e10"}
        for eq in EQUIPMENT:
            assert eq["state_model"] in valid_models, f"{eq['code']} has invalid state model"

    def test_all_equipment_have_max_queue_depth(self):
        from mes.core.demo.electronics_data import EQUIPMENT
        for eq in EQUIPMENT:
            assert eq["max_queue_depth"] >= 1

    def test_equipment_types_non_empty(self):
        from mes.core.demo.electronics_data import EQUIPMENT
        for eq in EQUIPMENT:
            assert eq["equipment_type"], f"{eq['code']} missing equipment_type"


class TestElecDataEquipmentMaterials:
    """Verify equipment-material assignments."""

    def test_assignment_count(self):
        from mes.core.demo.electronics_data import EQUIPMENT_MATERIALS
        assert len(EQUIPMENT_MATERIALS) == 8

    def test_assignments_reference_valid_equipment(self):
        from mes.core.demo.electronics_data import EQUIPMENT_MATERIALS, EQUIPMENT
        eq_codes = {eq["code"] for eq in EQUIPMENT}
        for em in EQUIPMENT_MATERIALS:
            assert em["equipment_code"] in eq_codes

    def test_all_assignments_target_finished_product(self):
        from mes.core.demo.electronics_data import EQUIPMENT_MATERIALS
        for em in EQUIPMENT_MATERIALS:
            assert em["material_code"] == "FG-ECB-100"

    def test_design_speeds_positive(self):
        from mes.core.demo.electronics_data import EQUIPMENT_MATERIALS
        for em in EQUIPMENT_MATERIALS:
            assert em["design_speed"] > 0
            assert em["target_oee"] > 0


# ═════════════════════════════════════════════════════════════════════
# 2. SERVICE & ROUTE IMPORTS
# ═════════════════════════════════════════════════════════════════════


class TestElecServiceImports:
    """Verify service functions are importable."""

    def test_seed_electronics_erp_data_importable(self):
        from mes.core.demo.service import seed_electronics_erp_data
        assert callable(seed_electronics_erp_data)

    def test_seed_electronics_plant_data_importable(self):
        from mes.core.demo.service import seed_electronics_plant_data
        assert callable(seed_electronics_plant_data)


class TestElecDemoRouteRegistration:
    """Verify demo routes include electronics endpoints."""

    def test_demo_router_has_electronics_erp_endpoint(self):
        from mes.core.demo.routes import router
        paths = [r.path for r in router.routes]
        assert any("seed-electronics-erp" in p for p in paths)

    def test_demo_router_has_electronics_plant_endpoint(self):
        from mes.core.demo.routes import router
        paths = [r.path for r in router.routes]
        assert any("seed-electronics-plant" in p for p in paths)

    def test_main_app_includes_electronics_routes(self):
        from mes.main import create_app
        app = create_app()
        route_paths = [r.path for r in app.routes]
        assert "/api/v1/demo/seed-electronics-erp" in route_paths
        assert "/api/v1/demo/seed-electronics-plant" in route_paths


# ═════════════════════════════════════════════════════════════════════
# 3. DATA INTEGRITY CROSS-CHECKS
# ═════════════════════════════════════════════════════════════════════


class TestElecDataIntegrity:
    """Cross-module data consistency checks."""

    def test_step_work_cell_codes_exist(self):
        from mes.core.demo.electronics_data import STEPS, WORK_CELLS
        wc_codes = {wc["code"] for wc in WORK_CELLS}
        for s in STEPS:
            assert s["work_cell_code"] in wc_codes, f"Step {s['sequence']} refs invalid WC"

    def test_data_def_count_matches_param_count_for_production(self):
        """Data defs and step params should have same count for production steps."""
        from mes.core.demo.electronics_data import STEP_PARAMS, DATA_DEFS, STEPS
        production_seqs = {s["sequence"] for s in STEPS if s["step_type"] == "production"}
        for seq in production_seqs:
            params = len(STEP_PARAMS.get(seq, []))
            defs = len(DATA_DEFS.get(seq, []))
            assert params == defs, f"Step {seq}: {params} params vs {defs} data defs"

    def test_no_code_collision_with_cpg(self):
        """Electronics codes must not collide with CPG codes."""
        from mes.core.demo.electronics_data import MATERIALS as ELEC_MAT
        from mes.core.demo.cpg_data import MATERIALS as CPG_MAT
        elec_codes = {m["code"] for m in ELEC_MAT}
        cpg_codes = {m["code"] for m in CPG_MAT}
        assert elec_codes.isdisjoint(cpg_codes), "Material code collision between demos"

    def test_equipment_codes_no_collision_with_cpg(self):
        """Equipment codes must not collide with CPG equipment codes."""
        from mes.core.demo.electronics_data import EQUIPMENT as ELEC_EQ
        from mes.core.demo.cpg_data import EQUIPMENT as CPG_EQ
        elec_codes = {eq["code"] for eq in ELEC_EQ}
        cpg_codes = {eq["code"] for eq in CPG_EQ}
        assert elec_codes.isdisjoint(cpg_codes), "Equipment code collision between demos"
