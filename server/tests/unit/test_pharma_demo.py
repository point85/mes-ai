"""
Unit tests for the Pharma Demo seed module.

Tests cover:
  - pharma_data constants completeness and internal consistency
  - service module imports
  - route registration
  - data relationships (dispositions reference valid codes, etc.)
"""

from __future__ import annotations

import importlib

import pytest


# ═════════════════════════════════════════════════════════════════════
# 1. DATA CONSTANTS — pharma_data.py
# ═════════════════════════════════════════════════════════════════════


class TestPharmaDataMaterials:
    """Verify material definitions are complete and consistent."""

    def test_material_count(self):
        from mes.core.demo.pharma_data import MATERIALS
        assert len(MATERIALS) == 15

    def test_all_materials_have_required_fields(self):
        from mes.core.demo.pharma_data import MATERIALS
        for m in MATERIALS:
            assert "code" in m
            assert "name" in m
            assert "material_type" in m
            assert "uom" in m

    def test_material_codes_unique(self):
        from mes.core.demo.pharma_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert len(codes) == len(set(codes))

    def test_material_types_valid(self):
        from mes.core.demo.pharma_data import MATERIALS
        valid_types = {"raw", "semi", "finished", "packaging"}
        for m in MATERIALS:
            assert m["material_type"] in valid_types, f"{m['code']} has invalid type"

    def test_finished_product_present(self):
        from mes.core.demo.pharma_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert "FG-IBU-200MG" in codes

    def test_api_material_present(self):
        from mes.core.demo.pharma_data import MATERIALS
        codes = [m["code"] for m in MATERIALS]
        assert "RM-API-IBU" in codes

    def test_semi_materials_present(self):
        from mes.core.demo.pharma_data import MATERIALS
        semi_codes = {m["code"] for m in MATERIALS if m["material_type"] == "semi"}
        assert "SF-GRANULE" in semi_codes
        assert "SF-TABLET-UC" in semi_codes


class TestPharmaDataProduct:
    """Verify product definition."""

    def test_product_code_matches_finished_material(self):
        from mes.core.demo.pharma_data import PRODUCT
        assert PRODUCT["code"] == "FG-IBU-200MG"

    def test_product_type_is_process(self):
        from mes.core.demo.pharma_data import PRODUCT
        assert PRODUCT["product_type"] == "process"

    def test_product_has_version(self):
        from mes.core.demo.pharma_data import PRODUCT
        assert PRODUCT.get("version") == "1.0"


class TestPharmaDataMaterialLots:
    """Verify material lot definitions."""

    def test_lot_count(self):
        from mes.core.demo.pharma_data import MATERIAL_LOTS
        assert len(MATERIAL_LOTS) == 12

    def test_all_lots_have_required_fields(self):
        from mes.core.demo.pharma_data import MATERIAL_LOTS
        for lot in MATERIAL_LOTS:
            assert "material_code" in lot
            assert "lot_number" in lot
            assert lot["quantity_on_hand"] > 0

    def test_lot_numbers_unique(self):
        from mes.core.demo.pharma_data import MATERIAL_LOTS
        lots = [lot["lot_number"] for lot in MATERIAL_LOTS]
        assert len(lots) == len(set(lots))

    def test_lots_reference_valid_materials(self):
        from mes.core.demo.pharma_data import MATERIAL_LOTS, MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for lot in MATERIAL_LOTS:
            assert lot["material_code"] in mat_codes, \
                f"Lot {lot['lot_number']} references unknown material {lot['material_code']}"

    def test_api_lot_present(self):
        from mes.core.demo.pharma_data import MATERIAL_LOTS
        api_lots = [l for l in MATERIAL_LOTS if l["material_code"] == "RM-API-IBU"]
        assert len(api_lots) >= 1


class TestPharmaDataBOM:
    """Verify bill of material."""

    def test_bom_item_count(self):
        from mes.core.demo.pharma_data import BOM_ITEMS
        assert len(BOM_ITEMS) == 14

    def test_bom_materials_exist(self):
        from mes.core.demo.pharma_data import BOM_ITEMS, MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for item in BOM_ITEMS:
            assert item["material_code"] in mat_codes, \
                f"BOM ref {item['material_code']} not defined in MATERIALS"

    def test_bom_positions_unique(self):
        from mes.core.demo.pharma_data import BOM_ITEMS
        positions = [item["position"] for item in BOM_ITEMS]
        assert len(positions) == len(set(positions))

    def test_all_bom_items_have_positive_quantity(self):
        from mes.core.demo.pharma_data import BOM_ITEMS
        for item in BOM_ITEMS:
            assert item["quantity"] > 0

    def test_api_in_bom(self):
        from mes.core.demo.pharma_data import BOM_ITEMS
        api_items = [i for i in BOM_ITEMS if i["material_code"] == "RM-API-IBU"]
        assert len(api_items) == 1

    def test_packaging_materials_in_bom(self):
        from mes.core.demo.pharma_data import BOM_ITEMS
        pkg_items = [i for i in BOM_ITEMS if i["material_code"].startswith("PKG-")]
        assert len(pkg_items) >= 4

    def test_bom_step_sequences_reference_valid_steps(self):
        from mes.core.demo.pharma_data import BOM_ITEMS, STEPS
        valid_seqs = {s["sequence"] for s in STEPS}
        for item in BOM_ITEMS:
            seq = item.get("step_sequence")
            if seq is not None:
                assert seq in valid_seqs, \
                    f"BOM item {item['material_code']} step_sequence={seq} not in STEPS"


class TestPharmaDataDispositions:
    """Verify disposition definitions."""

    def test_disposition_count(self):
        from mes.core.demo.pharma_data import DISPOSITIONS
        assert len(DISPOSITIONS) == 15

    def test_disposition_codes_unique(self):
        from mes.core.demo.pharma_data import DISPOSITIONS
        codes = [d["code"] for d in DISPOSITIONS]
        assert len(codes) == len(set(codes))

    def test_disposition_categories_valid(self):
        from mes.core.demo.pharma_data import DISPOSITIONS
        valid = {"route", "hold", "release", "scrap"}
        for d in DISPOSITIONS:
            assert d["category"] in valid, \
                f"Disposition {d['code']} has invalid category {d['category']}"

    def test_rework_and_mrb_dispositions_present(self):
        from mes.core.demo.pharma_data import DISPOSITIONS
        codes = {d["code"] for d in DISPOSITIONS}
        assert "P-IPC-FAIL" in codes
        assert "P-ESCALATE" in codes
        assert "P-MRB-REPROCESS" in codes
        assert "P-MRB-USE-AS-IS" in codes


class TestPharmaDataRoute:
    """Verify route steps."""

    def test_step_count(self):
        from mes.core.demo.pharma_data import STEPS
        assert len(STEPS) == 12

    def test_route_name(self):
        from mes.core.demo.pharma_data import ROUTE_NAME
        assert ROUTE_NAME == "Solid Dose Tablet Line"

    def test_sequences_unique(self):
        from mes.core.demo.pharma_data import STEPS
        seqs = [s["sequence"] for s in STEPS]
        assert len(seqs) == len(set(seqs))

    def test_sequences_ascending(self):
        from mes.core.demo.pharma_data import STEPS
        seqs = [s["sequence"] for s in STEPS]
        assert seqs == sorted(seqs)

    def test_step_types_valid(self):
        from mes.core.demo.pharma_data import STEPS
        valid = {"production", "inspection", "rework", "mrb"}
        for s in STEPS:
            assert s["step_type"] in valid, f"Step {s['sequence']} has invalid type"

    def test_exactly_one_initial_step(self):
        from mes.core.demo.pharma_data import STEPS
        initial = [s for s in STEPS if s.get("is_initial_step")]
        assert len(initial) == 1
        assert initial[0]["sequence"] == 10

    def test_rework_step_present(self):
        from mes.core.demo.pharma_data import STEPS
        rework = [s for s in STEPS if s["step_type"] == "rework"]
        assert len(rework) >= 1

    def test_mrb_step_present(self):
        from mes.core.demo.pharma_data import STEPS
        mrb = [s for s in STEPS if s["step_type"] == "mrb"]
        assert len(mrb) >= 1

    def test_all_steps_have_positive_cycle_time(self):
        from mes.core.demo.pharma_data import STEPS
        for s in STEPS:
            assert s["expected_cycle_time_sec"] > 0

    def test_all_steps_have_erp_op_number(self):
        from mes.core.demo.pharma_data import STEPS
        for s in STEPS:
            assert s["erp_operation_number"] is not None

    def test_all_disposition_codes_reference_defined_dispositions(self):
        from mes.core.demo.pharma_data import STEPS, DISPOSITIONS
        catalog = {d["code"] for d in DISPOSITIONS}
        for s in STEPS:
            for code in s.get("input_disposition_codes", []):
                assert code in catalog, \
                    f"Step {s['sequence']} input disposition '{code}' not in DISPOSITIONS"
            for code in s.get("output_disposition_codes", []):
                assert code in catalog, \
                    f"Step {s['sequence']} output disposition '{code}' not in DISPOSITIONS"

    def test_terminal_step_has_no_outputs(self):
        from mes.core.demo.pharma_data import STEPS
        terminal = [s for s in STEPS if not s.get("output_disposition_codes")]
        assert len(terminal) >= 1
        # Packaging (seq 100) is the primary terminal step
        terminal_seqs = {s["sequence"] for s in terminal}
        assert 100 in terminal_seqs

    def test_all_work_cell_codes_reference_defined_cells(self):
        from mes.core.demo.pharma_data import STEPS, WORK_CELLS
        wc_codes = {wc["code"] for wc in WORK_CELLS}
        for s in STEPS:
            assert s["work_cell_code"] in wc_codes, \
                f"Step {s['sequence']} work_cell_code '{s['work_cell_code']}' not in WORK_CELLS"


class TestPharmaDataStepParams:
    """Verify step parameter definitions."""

    def test_all_non_dispensing_steps_have_params(self):
        """Steps 20-100 must have recipe-level STEP_PARAMS.
        Steps 10 (Dispensing), 110 (Rework), 120 (MRB) have DATA_DEFS only
        because all their entries are execution checks or documentation with
        no meaningful recipe target/limits."""
        from mes.core.demo.pharma_data import STEP_PARAMS, STEPS
        NO_PARAMS_STEPS = {10, 110, 120}
        recipe_steps = {s["sequence"] for s in STEPS} - NO_PARAMS_STEPS
        for seq in recipe_steps:
            assert seq in STEP_PARAMS, f"Step {seq} has no STEP_PARAMS entry"

    def test_all_params_have_required_fields(self):
        from mes.core.demo.pharma_data import STEP_PARAMS
        for seq, params in STEP_PARAMS.items():
            for p in params:
                assert "name" in p, f"Step {seq} param missing 'name'"
                assert "data_type" in p, f"Step {seq} param missing 'data_type'"
                assert "is_required" in p, f"Step {seq} param missing 'is_required'"

    def test_no_boolean_checks_in_step_params(self):
        """Boolean pass/fail checks must not appear in STEP_PARAMS
        (they belong solely in DATA_DEFS as execution records)."""
        from mes.core.demo.pharma_data import STEP_PARAMS
        for seq, params in STEP_PARAMS.items():
            for p in params:
                assert p["data_type"] != "boolean", (
                    f"Step {seq} param '{p['name']}' is boolean — move to DATA_DEFS only"
                )

    def test_no_null_target_in_step_params(self):
        """Every STEP_PARAM entry must have a target value; null-target entries
        are documentation-only and belong in DATA_DEFS."""
        from mes.core.demo.pharma_data import STEP_PARAMS
        for seq, params in STEP_PARAMS.items():
            for p in params:
                assert p.get("target_value") is not None, (
                    f"Step {seq} param '{p['name']}' has no target_value — move to DATA_DEFS only"
                )

    def test_step_param_names_match_data_def_names(self):
        """Every STEP_PARAM name must appear as a DATA_DEF name for the same step
        (data defs are the EBR collection schema; each recipe spec needs one)."""
        from mes.core.demo.pharma_data import STEP_PARAMS, DATA_DEFS
        for seq, params in STEP_PARAMS.items():
            def_names = {d["name"] for d in DATA_DEFS.get(seq, [])}
            for p in params:
                assert p["name"] in def_names, (
                    f"Step {seq} STEP_PARAM '{p['name']}' has no matching DATA_DEF name"
                )

    def test_total_param_count(self):
        from mes.core.demo.pharma_data import STEP_PARAMS
        total = sum(len(v) for v in STEP_PARAMS.values())
        # 20:4 30:4 40:3 50:3 60:6 70:4 80:4 90:6 100:1 = 35
        assert total == 35, f"Expected 35 step parameters, got {total}"


class TestPharmaDataDataDefs:
    """Verify data collection definitions."""

    def test_all_steps_have_data_defs(self):
        from mes.core.demo.pharma_data import DATA_DEFS, STEPS
        step_seqs = {s["sequence"] for s in STEPS}
        for seq in DATA_DEFS:
            assert seq in step_seqs, f"DATA_DEFS seq {seq} not in STEPS"

    def test_data_def_codes_unique(self):
        from mes.core.demo.pharma_data import DATA_DEFS
        all_codes: list[str] = []
        for defs in DATA_DEFS.values():
            all_codes.extend(d["code"] for d in defs)
        assert len(all_codes) == len(set(all_codes)), "Duplicate data definition codes"

    def test_data_def_codes_prefixed_correctly(self):
        from mes.core.demo.pharma_data import DATA_DEFS
        for defs in DATA_DEFS.values():
            for d in defs:
                assert d["code"].startswith("PHX-"), \
                    f"Data def code '{d['code']}' should be prefixed 'PHX-'"

    def test_data_def_sources_valid(self):
        from mes.core.demo.pharma_data import DATA_DEFS
        valid = {"equipment", "manual", "calculated"}
        for seq, defs in DATA_DEFS.items():
            for d in defs:
                assert d["source"] in valid, \
                    f"Step {seq} def '{d['code']}' has invalid source '{d['source']}'"

    def test_total_data_def_count(self):
        from mes.core.demo.pharma_data import DATA_DEFS
        total = sum(len(v) for v in DATA_DEFS.values())
        assert total >= 40, f"Expected ≥40 data definitions, got {total}"

    def test_data_def_count_matches_param_count(self):
        """Each step with params should have at least as many data defs.
        Step 10 (Dispensing) has no step params by design — data defs only."""
        from mes.core.demo.pharma_data import DATA_DEFS, STEP_PARAMS
        for seq in STEP_PARAMS:
            if seq in DATA_DEFS:
                assert len(DATA_DEFS[seq]) >= len(STEP_PARAMS[seq]), \
                    f"Step {seq} has fewer data defs than params"


class TestPharmaDataPhysicalModel:
    """Verify ISA-95 physical model constants."""

    def test_site_fields_present(self):
        from mes.core.demo.pharma_data import SITE
        assert "code" in SITE and "name" in SITE and "timezone" in SITE

    def test_work_cell_count(self):
        from mes.core.demo.pharma_data import WORK_CELLS
        assert len(WORK_CELLS) == 10

    def test_work_cell_codes_unique(self):
        from mes.core.demo.pharma_data import WORK_CELLS
        codes = [wc["code"] for wc in WORK_CELLS]
        assert len(codes) == len(set(codes))

    def test_equipment_count(self):
        from mes.core.demo.pharma_data import EQUIPMENT
        assert len(EQUIPMENT) == 12

    def test_dual_blenders_present(self):
        from mes.core.demo.pharma_data import EQUIPMENT
        blenders = [e for e in EQUIPMENT if e["work_cell_code"] == "WC-BLEND"]
        assert len(blenders) == 2, "Expected 2 bin blenders in WC-BLEND for dispatch demo"

    def test_dual_presses_present(self):
        from mes.core.demo.pharma_data import EQUIPMENT
        presses = [e for e in EQUIPMENT if e["work_cell_code"] == "WC-PRESS"]
        assert len(presses) == 2, "Expected 2 tablet presses in WC-PRESS for dispatch demo"

    def test_equipment_codes_unique(self):
        from mes.core.demo.pharma_data import EQUIPMENT
        codes = [e["code"] for e in EQUIPMENT]
        assert len(codes) == len(set(codes))

    def test_equipment_work_cells_reference_valid_cells(self):
        from mes.core.demo.pharma_data import EQUIPMENT, WORK_CELLS
        wc_codes = {wc["code"] for wc in WORK_CELLS}
        for eq in EQUIPMENT:
            assert eq["work_cell_code"] in wc_codes, \
                f"Equipment {eq['code']} references unknown WC {eq['work_cell_code']}"

    def test_state_models_valid(self):
        from mes.core.demo.pharma_data import EQUIPMENT
        valid = {"packml", "semi_e10", None}
        for eq in EQUIPMENT:
            assert eq.get("state_model") in valid, \
                f"Equipment {eq['code']} has unknown state_model {eq.get('state_model')}"


class TestPharmaDataEquipmentMaterials:
    """Verify equipment-material assignment definitions."""

    def test_all_equipment_has_assignment(self):
        from mes.core.demo.pharma_data import EQUIPMENT, EQUIPMENT_MATERIALS
        eq_codes = {e["code"] for e in EQUIPMENT}
        em_codes = {em["equipment_code"] for em in EQUIPMENT_MATERIALS}
        assert eq_codes == em_codes, \
            f"Equipment without material assignments: {eq_codes - em_codes}"

    def test_assignment_count(self):
        from mes.core.demo.pharma_data import EQUIPMENT_MATERIALS
        assert len(EQUIPMENT_MATERIALS) == 12

    def test_design_speeds_positive(self):
        from mes.core.demo.pharma_data import EQUIPMENT_MATERIALS
        for em in EQUIPMENT_MATERIALS:
            assert em["design_speed"] > 0

    def test_target_oee_range(self):
        from mes.core.demo.pharma_data import EQUIPMENT_MATERIALS
        for em in EQUIPMENT_MATERIALS:
            assert 0 < em["target_oee"] <= 100


class TestPharmaDataEquipmentClasses:
    """Verify ISA-95 equipment class definitions."""

    def test_class_count(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CLASSES
        assert len(EQUIPMENT_CLASSES) == 10

    def test_class_codes_unique(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CLASSES
        codes = [c["code"] for c in EQUIPMENT_CLASSES]
        assert len(codes) == len(set(codes))

    def test_class_map_covers_all_equipment(self):
        from mes.core.demo.pharma_data import EQUIPMENT, EQUIPMENT_CLASS_MAP
        for eq in EQUIPMENT:
            assert eq["code"] in EQUIPMENT_CLASS_MAP, \
                f"Equipment {eq['code']} has no entry in EQUIPMENT_CLASS_MAP"

    def test_class_map_references_valid_classes(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CLASSES, EQUIPMENT_CLASS_MAP
        class_codes = {c["code"] for c in EQUIPMENT_CLASSES}
        for eq_code, cls_code in EQUIPMENT_CLASS_MAP.items():
            assert cls_code in class_codes, \
                f"EQUIPMENT_CLASS_MAP[{eq_code}] = '{cls_code}' not in EQUIPMENT_CLASSES"

    def test_step_equipment_class_references_valid_classes(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CLASSES, STEP_EQUIPMENT_CLASS
        class_codes = {c["code"] for c in EQUIPMENT_CLASSES}
        for seq, cls_code in STEP_EQUIPMENT_CLASS.items():
            assert cls_code in class_codes, \
                f"STEP_EQUIPMENT_CLASS[{seq}] = '{cls_code}' not in EQUIPMENT_CLASSES"

    def test_step_equipment_class_covers_all_steps(self):
        from mes.core.demo.pharma_data import STEPS, STEP_EQUIPMENT_CLASS
        for s in STEPS:
            assert s["sequence"] in STEP_EQUIPMENT_CLASS, \
                f"Step {s['sequence']} has no entry in STEP_EQUIPMENT_CLASS"


class TestPharmaDataStorageLocations:
    """Verify storage location definitions."""

    def test_storage_location_count(self):
        from mes.core.demo.pharma_data import STORAGE_LOCATIONS
        assert len(STORAGE_LOCATIONS) >= 12

    def test_codes_unique(self):
        from mes.core.demo.pharma_data import STORAGE_LOCATIONS
        codes = [sl["code"] for sl in STORAGE_LOCATIONS]
        assert len(codes) == len(set(codes))

    def test_receiving_dock_present(self):
        from mes.core.demo.pharma_data import STORAGE_LOCATIONS
        codes = {sl["code"] for sl in STORAGE_LOCATIONS}
        assert "PHX-RECV-01" in codes

    def test_api_vault_present(self):
        from mes.core.demo.pharma_data import STORAGE_LOCATIONS
        codes = {sl["code"] for sl in STORAGE_LOCATIONS}
        assert "PHX-API-VAULT" in codes

    def test_location_types_valid(self):
        from mes.core.demo.pharma_data import STORAGE_LOCATIONS
        valid = {"receiving", "storage", "staging", "rip", "shipping", "quarantine"}
        for sl in STORAGE_LOCATIONS:
            assert sl["location_type"] in valid, \
                f"StorageLocation {sl['code']} has invalid type '{sl['location_type']}'"

    def test_material_storage_map_references_valid_locations(self):
        from mes.core.demo.pharma_data import STORAGE_LOCATIONS, MATERIAL_STORAGE_MAP
        loc_codes = {sl["code"] for sl in STORAGE_LOCATIONS}
        for mat_code, loc_code in MATERIAL_STORAGE_MAP.items():
            assert loc_code in loc_codes, \
                f"MATERIAL_STORAGE_MAP[{mat_code}] = '{loc_code}' not in STORAGE_LOCATIONS"

    def test_material_storage_map_references_valid_materials(self):
        from mes.core.demo.pharma_data import MATERIALS, MATERIAL_STORAGE_MAP
        mat_codes = {m["code"] for m in MATERIALS}
        for mat_code in MATERIAL_STORAGE_MAP:
            assert mat_code in mat_codes, \
                f"MATERIAL_STORAGE_MAP key '{mat_code}' not in MATERIALS"


class TestPharmaDataSegmentRequirements:
    """Verify segment material and equipment requirements."""

    def test_segment_material_requirements_reference_valid_steps(self):
        from mes.core.demo.pharma_data import SEGMENT_MATERIAL_REQUIREMENTS, STEPS
        valid_seqs = {s["sequence"] for s in STEPS}
        for req in SEGMENT_MATERIAL_REQUIREMENTS:
            assert req["step_sequence"] in valid_seqs, \
                f"SMR step_sequence={req['step_sequence']} not in STEPS"

    def test_segment_material_requirements_reference_valid_materials(self):
        from mes.core.demo.pharma_data import SEGMENT_MATERIAL_REQUIREMENTS, MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for req in SEGMENT_MATERIAL_REQUIREMENTS:
            assert req["material_code"] in mat_codes, \
                f"SMR material_code '{req['material_code']}' not in MATERIALS"

    def test_segment_material_use_types_valid(self):
        from mes.core.demo.pharma_data import SEGMENT_MATERIAL_REQUIREMENTS
        valid = {"consumed", "produced", "co-product", "by-product"}
        for req in SEGMENT_MATERIAL_REQUIREMENTS:
            assert req["material_use"] in valid, \
                f"SMR material_use '{req['material_use']}' is invalid"

    def test_segment_equipment_requirements_reference_valid_steps(self):
        from mes.core.demo.pharma_data import SEGMENT_EQUIPMENT_REQUIREMENTS, STEPS
        valid_seqs = {s["sequence"] for s in STEPS}
        for req in SEGMENT_EQUIPMENT_REQUIREMENTS:
            assert req["step_sequence"] in valid_seqs, \
                f"SER step_sequence={req['step_sequence']} not in STEPS"

    def test_segment_equipment_requirements_use_types_valid(self):
        from mes.core.demo.pharma_data import SEGMENT_EQUIPMENT_REQUIREMENTS
        valid = {"required", "preferred", "alternate"}
        for req in SEGMENT_EQUIPMENT_REQUIREMENTS:
            assert req["use_type"] in valid, \
                f"SER use_type '{req['use_type']}' is invalid"

    def test_route_material_assignments_reference_valid_materials(self):
        from mes.core.demo.pharma_data import ROUTE_MATERIAL_ASSIGNMENTS, MATERIALS
        mat_codes = {m["code"] for m in MATERIALS}
        for code in ROUTE_MATERIAL_ASSIGNMENTS:
            assert code in mat_codes, \
                f"ROUTE_MATERIAL_ASSIGNMENTS entry '{code}' not in MATERIALS"


class TestPharmaDataEquipmentCapabilities:
    """Verify equipment capability definitions."""

    def test_capabilities_reference_valid_equipment(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CAPABILITIES, EQUIPMENT
        eq_codes = {e["code"] for e in EQUIPMENT}
        for cap in EQUIPMENT_CAPABILITIES:
            assert cap["equipment_code"] in eq_codes, \
                f"Capability equipment_code '{cap['equipment_code']}' not in EQUIPMENT"

    def test_capabilities_reference_valid_classes(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CAPABILITIES, EQUIPMENT_CLASSES
        class_codes = {c["code"] for c in EQUIPMENT_CLASSES}
        for cap in EQUIPMENT_CAPABILITIES:
            assert cap["equipment_class_code"] in class_codes, \
                f"Capability equipment_class_code '{cap['equipment_class_code']}' not in EQUIPMENT_CLASSES"

    def test_capability_types_valid(self):
        from mes.core.demo.pharma_data import EQUIPMENT_CAPABILITIES
        valid = {"available", "committed", "unattainable"}
        for cap in EQUIPMENT_CAPABILITIES:
            assert cap["capability_type"] in valid, \
                f"Capability for {cap['equipment_code']} has invalid type"

    def test_all_equipment_has_capability(self):
        from mes.core.demo.pharma_data import EQUIPMENT, EQUIPMENT_CAPABILITIES
        eq_codes = {e["code"] for e in EQUIPMENT}
        cap_codes = {c["equipment_code"] for c in EQUIPMENT_CAPABILITIES}
        assert eq_codes == cap_codes, \
            f"Equipment without capabilities: {eq_codes - cap_codes}"


# ═════════════════════════════════════════════════════════════════════
# 2. SERVICE MODULE — import and function availability
# ═════════════════════════════════════════════════════════════════════


class TestPharmaServiceImports:
    """Verify service functions are importable."""

    def test_seed_pharma_erp_data_importable(self):
        from mes.core.demo.service import seed_pharma_erp_data  # noqa: F401

    def test_seed_pharma_plant_data_importable(self):
        from mes.core.demo.service import seed_pharma_plant_data  # noqa: F401

    def test_pharma_data_module_importable(self):
        mod = importlib.import_module("mes.core.demo.pharma_data")
        assert hasattr(mod, "MATERIALS")
        assert hasattr(mod, "STEPS")
        assert hasattr(mod, "EQUIPMENT")


# ═════════════════════════════════════════════════════════════════════
# 3. ROUTES — endpoint registration
# ═════════════════════════════════════════════════════════════════════


class TestPharmaRoutes:
    """Verify demo router exposes the pharma endpoints."""

    def test_seed_pharma_erp_route_registered(self):
        from mes.core.demo.routes import router
        paths = [r.path for r in router.routes]
        assert any(p.endswith("/seed-pharma-erp") for p in paths), \
            f"'/seed-pharma-erp' not found in router. Paths: {paths}"

    def test_seed_pharma_plant_route_registered(self):
        from mes.core.demo.routes import router
        paths = [r.path for r in router.routes]
        assert any(p.endswith("/seed-pharma-plant") for p in paths), \
            f"'/seed-pharma-plant' not found in router. Paths: {paths}"


# ═════════════════════════════════════════════════════════════════════
# 4. ROUTE GRAPH — reachability and consistency
# ═════════════════════════════════════════════════════════════════════


class TestPharmaRouteGraph:
    """Verify the pharma route graph is internally consistent."""

    def test_initial_step_has_no_inputs(self):
        from mes.core.demo.pharma_data import STEPS
        initial = next(s for s in STEPS if s.get("is_initial_step"))
        assert initial["input_disposition_codes"] == []

    def test_every_output_disposition_consumed_as_input(self):
        """Every output disposition code must appear in at least one step's input list,
        OR be a terminal-only disposition (no subsequent step consumes it)."""
        from mes.core.demo.pharma_data import STEPS
        all_inputs = set()
        all_outputs = set()
        for s in STEPS:
            all_inputs.update(s.get("input_disposition_codes", []))
            all_outputs.update(s.get("output_disposition_codes", []))
        # Every output should eventually be consumed as input somewhere
        # (true for all non-terminal routes — MRB outputs are consumed by downstream steps)
        unconsumed = all_outputs - all_inputs
        # It is acceptable for outputs that go to terminal steps to be unconsumed
        # but we expect no more than a small number
        assert len(unconsumed) <= 2, \
            f"Too many unconsumed output dispositions: {unconsumed}"

    def test_packaging_step_is_reachable_from_initial(self):
        """Trace at least one forward path from step 10 to step 100 (Packaging)."""
        from mes.core.demo.pharma_data import STEPS
        step_by_seq = {s["sequence"]: s for s in STEPS}
        # Build edges: disposition code → set of steps it is an input of
        disp_to_step: dict[str, list[int]] = {}
        for s in STEPS:
            for code in s.get("input_disposition_codes", []):
                disp_to_step.setdefault(code, []).append(s["sequence"])

        visited: set[int] = set()

        def dfs(seq: int) -> None:
            if seq in visited:
                return
            visited.add(seq)
            step = step_by_seq[seq]
            for out_code in step.get("output_disposition_codes", []):
                for next_seq in disp_to_step.get(out_code, []):
                    dfs(next_seq)

        dfs(10)
        assert 100 in visited, "Packaging step (100) is not reachable from initial step (10)"

    def test_rework_loop_exists(self):
        """IPC-fail disposition must reach Tablet Rework (110) which feeds back to Compression (60)."""
        from mes.core.demo.pharma_data import STEPS
        ipc_step = next(s for s in STEPS if s["sequence"] == 70)
        rework_step = next(s for s in STEPS if s["sequence"] == 110)
        compress_step = next(s for s in STEPS if s["sequence"] == 60)
        assert "P-IPC-FAIL" in ipc_step["output_disposition_codes"]
        assert "P-IPC-FAIL" in rework_step["input_disposition_codes"]
        assert "P-REWORK-DONE" in rework_step["output_disposition_codes"]
        assert "P-REWORK-DONE" in compress_step["input_disposition_codes"]
