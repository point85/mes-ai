"""
Pharma Demo: Solid-Dose Tablet Manufacturing Line data constants.

Defines all materials, product, BOM, route steps, dispositions,
step parameters, data definitions, quality test, production orders,
and the ISA-95 physical hierarchy for a single-product pharmaceutical
tablet manufacturing demonstration scenario.

Product:   Ibuprofen 200 mg Film-Coated Tablets (30-pack blister)
Process:   Wet granulation → fluid-bed drying → milling → blending →
           compression → in-process control → film coating →
           release testing → blister packaging.
Tracking:  Lot/batch (process manufacturing, ISA-95 Part 1).
Regulatory context:
    cGMP  — 21 CFR Part 211 (US), EU GMP Annex 1/15 (EU)
    21 CFR Part 11 — electronic records / signatures
    ICH Q8/Q9/Q10 — quality by design, risk management, pharma quality system

Batch size: 50 000 tablets (≈ 14.5 kg uncoated core, ≈ 14.95 kg coated)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MATERIALS: list[dict] = [
    # Active Pharmaceutical Ingredient
    {"code": "RM-API-IBU",    "name": "Ibuprofen API",                   "material_type": "raw",       "uom": "kg"},
    # Excipients
    {"code": "RM-EXC-MCC",   "name": "Microcrystalline Cellulose PH101", "material_type": "raw",       "uom": "kg"},
    {"code": "RM-EXC-CCS",   "name": "Croscarmellose Sodium",            "material_type": "raw",       "uom": "kg"},
    {"code": "RM-EXC-PVP",   "name": "Povidone K30 (Binder)",           "material_type": "raw",       "uom": "kg"},
    {"code": "RM-EXC-MGST",  "name": "Magnesium Stearate",              "material_type": "raw",       "uom": "kg"},
    {"code": "RM-COAT-OPW",  "name": "Opadry White Film Coat",          "material_type": "raw",       "uom": "kg"},
    {"code": "RM-WATER-PW",  "name": "Purified Water (WFI Grade)",      "material_type": "raw",       "uom": "L"},
    # Semi-finished intermediates
    {"code": "SF-GRANULE",   "name": "Dried Granule Blend",             "material_type": "semi",      "uom": "kg"},
    {"code": "SF-TABLET-UC", "name": "Uncoated Tablet Core",            "material_type": "semi",      "uom": "EA"},
    # Primary packaging
    {"code": "PKG-BLISTER",  "name": "Blister Base Film PVC/PVDC",      "material_type": "packaging", "uom": "m"},
    {"code": "PKG-LIDDING",  "name": "Blister Lidding Foil (Alu)",      "material_type": "packaging", "uom": "m"},
    {"code": "PKG-CARTON",   "name": "Folding Carton (30-pack)",        "material_type": "packaging", "uom": "EA"},
    {"code": "PKG-INSERT",   "name": "Package Insert / SmPC Leaflet",   "material_type": "packaging", "uom": "EA"},
    {"code": "PKG-SEAL",     "name": "Tamper-Evident Seal",             "material_type": "packaging", "uom": "EA"},
    # Finished Good
    {"code": "FG-IBU-200MG", "name": "Ibuprofen 200 mg Tablets 30-pack","material_type": "finished",  "uom": "EA"},
]

# ---------------------------------------------------------------------------
# Material Lots  (initial inventory for demo)
# ---------------------------------------------------------------------------

MATERIAL_LOTS: list[dict] = [
    # API — high-security controlled substance vault
    {"material_code": "RM-API-IBU",   "lot_number": "LOT-API-IBU-2026A", "quantity_on_hand": 200.0,   "supplier": "BASF Pharma Solutions",  "received_date": "2026-01-10", "expiry_date": "2028-01-10"},
    # Excipients
    {"material_code": "RM-EXC-MCC",  "lot_number": "LOT-MCC-2026A",     "quantity_on_hand": 500.0,   "supplier": "FMC BioPolymer",          "received_date": "2026-02-01", "expiry_date": "2029-02-01"},
    {"material_code": "RM-EXC-CCS",  "lot_number": "LOT-CCS-2026A",     "quantity_on_hand": 50.0,    "supplier": "Ashland Inc.",             "received_date": "2026-02-01", "expiry_date": "2029-02-01"},
    {"material_code": "RM-EXC-PVP",  "lot_number": "LOT-PVP-2026A",     "quantity_on_hand": 80.0,    "supplier": "BASF SE",                  "received_date": "2026-02-15", "expiry_date": "2029-02-15"},
    {"material_code": "RM-EXC-MGST", "lot_number": "LOT-MGST-2026A",    "quantity_on_hand": 20.0,    "supplier": "Peter Greven GmbH",        "received_date": "2026-02-15", "expiry_date": "2029-02-15"},
    {"material_code": "RM-COAT-OPW", "lot_number": "LOT-OPW-2026A",     "quantity_on_hand": 30.0,    "supplier": "Colorcon Inc.",            "received_date": "2026-03-01", "expiry_date": "2028-03-01"},
    # Purified water generated on-site — seeded as a nominal lot
    {"material_code": "RM-WATER-PW", "lot_number": "LOT-WPW-2026A",     "quantity_on_hand": 5000.0,  "supplier": "On-site WFI System",       "received_date": "2026-01-01", "expiry_date": "2026-12-31"},
    # Packaging materials
    {"material_code": "PKG-BLISTER", "lot_number": "LOT-BLI-2026A",     "quantity_on_hand": 5000.0,  "supplier": "Bilcare AG",               "received_date": "2026-04-01", "expiry_date": "2029-04-01"},
    {"material_code": "PKG-LIDDING", "lot_number": "LOT-LID-2026A",     "quantity_on_hand": 5000.0,  "supplier": "Bilcare AG",               "received_date": "2026-04-01", "expiry_date": "2029-04-01"},
    {"material_code": "PKG-CARTON",  "lot_number": "LOT-CTN-2026A",     "quantity_on_hand": 10000.0, "supplier": "Graphic Packaging Intl.",  "received_date": "2026-04-15", "expiry_date": "2029-04-15"},
    {"material_code": "PKG-INSERT",  "lot_number": "LOT-INS-2026A",     "quantity_on_hand": 10000.0, "supplier": "PrintPharma Ltd.",         "received_date": "2026-04-15", "expiry_date": "2029-04-15"},
    {"material_code": "PKG-SEAL",    "lot_number": "LOT-SEL-2026A",     "quantity_on_hand": 20000.0, "supplier": "Selig Sealing Products",   "received_date": "2026-04-15", "expiry_date": "2031-04-15"},
]

# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

PRODUCT = {
    "code": "FG-IBU-200MG",
    "name": "Ibuprofen 200 mg Tablets 30-pack",
    "version": "1.0",
    "product_type": "process",
    "description": "Film-coated ibuprofen 200 mg tablets in a 30-cavity blister pack (cGMP, ICH Q8)",
    "uom": "EA",
}

# ---------------------------------------------------------------------------
# Bill of Material  (per batch = 50 000 tablets → 1 667 × 30-packs)
# ---------------------------------------------------------------------------

BOM_ITEMS: list[dict] = [
    # Dispensed at Dispensing step (seq 10)
    {"material_code": "RM-API-IBU",   "quantity": 10.0,   "uom": "kg",  "position": 10, "step_sequence": 10},
    {"material_code": "RM-EXC-MCC",  "quantity": 3.05,   "uom": "kg",  "position": 20, "step_sequence": 10},
    {"material_code": "RM-EXC-CCS",  "quantity": 0.625,  "uom": "kg",  "position": 30, "step_sequence": 10},
    {"material_code": "RM-EXC-PVP",  "quantity": 0.625,  "uom": "kg",  "position": 40, "step_sequence": 10},
    {"material_code": "RM-EXC-MGST", "quantity": 0.2,    "uom": "kg",  "position": 50, "step_sequence": 10},
    # Consumed at Granulation (seq 20) — binder solution water
    {"material_code": "RM-WATER-PW", "quantity": 0.5,    "uom": "L",   "position": 60, "step_sequence": 20},
    # Consumed at Film Coating (seq 80)
    {"material_code": "RM-COAT-OPW", "quantity": 0.45,   "uom": "kg",  "position": 70, "step_sequence": 80},
    # Intermediate tracking entries (no step — produced during processing)
    {"material_code": "SF-GRANULE",  "quantity": 14.5,   "uom": "kg",  "position": 80},
    {"material_code": "SF-TABLET-UC","quantity": 50000.0,"uom": "EA",  "position": 90},
    # Consumed at Packaging (seq 100)
    {"material_code": "PKG-BLISTER", "quantity": 16.7,   "uom": "m",   "position": 100, "step_sequence": 100},
    {"material_code": "PKG-LIDDING", "quantity": 16.7,   "uom": "m",   "position": 110, "step_sequence": 100},
    {"material_code": "PKG-CARTON",  "quantity": 1667.0, "uom": "EA",  "position": 120, "step_sequence": 100},
    {"material_code": "PKG-INSERT",  "quantity": 1667.0, "uom": "EA",  "position": 130, "step_sequence": 100},
    {"material_code": "PKG-SEAL",    "quantity": 1667.0, "uom": "EA",  "position": 140, "step_sequence": 100},
]

# ---------------------------------------------------------------------------
# Dispositions (top-level entities)
# ---------------------------------------------------------------------------

DISPOSITIONS: list[dict] = [
    # Per-edge dispositions for the solid-dose tablet route graph.
    # Each entry appears in exactly one step's output list AND at most
    # one step's input list (unambiguous (output → input) edges).
    {"code": "P-DISP-DONE",     "name": "Dispensing Complete",       "description": "All materials dispensed & reconciled; advance to granulation",    "category": "route"},
    {"code": "P-GRAN-DONE",     "name": "Granulation Complete",      "description": "Wet granulation endpoint met; advance to drying",                 "category": "route"},
    {"code": "P-DRY-DONE",      "name": "Drying Complete",           "description": "LOD within spec; advance to milling",                            "category": "route"},
    {"code": "P-MILL-DONE",     "name": "Milling Complete",          "description": "Particle size within spec; advance to blending",                  "category": "route"},
    {"code": "P-BLEND-DONE",    "name": "Blending Complete",         "description": "Content uniformity acceptable; advance to compression",           "category": "route"},
    {"code": "P-COMP-DONE",     "name": "Compression Complete",      "description": "Tablet compression finished; advance to IPC check",               "category": "route"},
    {"code": "P-IPC-PASS",      "name": "IPC Pass",                  "description": "In-process checks passed; advance to film coating",               "category": "route"},
    {"code": "P-IPC-FAIL",      "name": "IPC Fail",                  "description": "In-process check out-of-spec; route to tablet rework",            "category": "route"},
    {"code": "P-ESCALATE",      "name": "Escalate to MRB",           "description": "Repeated IPC failure or critical deviation; send to MRB",         "category": "hold"},
    {"code": "P-COAT-DONE",     "name": "Film Coating Complete",     "description": "Weight gain and appearance within spec; advance to release test",  "category": "route"},
    {"code": "P-REL-PASS",      "name": "Release Test Pass",         "description": "All QC release criteria met; batch released for packaging",        "category": "route"},
    {"code": "P-REL-FAIL",      "name": "Release Test Fail",         "description": "QC release failure; route to MRB for disposition",                "category": "route"},
    {"code": "P-REWORK-DONE",   "name": "Tablet Rework Complete",    "description": "Rework/reprocess complete; return to compression",                "category": "route"},
    {"code": "P-MRB-REPROCESS", "name": "MRB → Reprocess",           "description": "MRB disposition: reprocess tablets",                             "category": "hold"},
    {"code": "P-MRB-USE-AS-IS", "name": "MRB → Approve As-Is",       "description": "MRB disposition: release without rework; advance to coating",     "category": "hold"},
]

# ---------------------------------------------------------------------------
# Route Steps
# ---------------------------------------------------------------------------

ROUTE_NAME = "Solid Dose Tablet Line"

STEPS: list[dict] = [
    {
        "sequence":   10,
        "name": "Dispensing",
        "step_type": "production",
        "work_cell_code": "WC-DISP",
        "expected_cycle_time_sec": 1800.0,
        "erp_operation_number": "0010",
        "is_initial_step": True,
        "input_disposition_codes": [],
        "output_disposition_codes": ["P-DISP-DONE"],
    },
    {
        "sequence":   20,
        "name": "Wet Granulation",
        "step_type": "production",
        "work_cell_code": "WC-GRAN",
        "expected_cycle_time_sec": 2700.0,
        "erp_operation_number": "0020",
        "input_disposition_codes": ["P-DISP-DONE"],
        "output_disposition_codes": ["P-GRAN-DONE"],
    },
    {
        "sequence":   30,
        "name": "Fluid Bed Drying",
        "step_type": "production",
        "work_cell_code": "WC-DRY",
        "expected_cycle_time_sec": 3600.0,
        "erp_operation_number": "0030",
        "input_disposition_codes": ["P-GRAN-DONE"],
        "output_disposition_codes": ["P-DRY-DONE"],
    },
    {
        "sequence":   40,
        "name": "Milling",
        "step_type": "production",
        "work_cell_code": "WC-MILL",
        "expected_cycle_time_sec": 1200.0,
        "erp_operation_number": "0040",
        "input_disposition_codes": ["P-DRY-DONE"],
        "output_disposition_codes": ["P-MILL-DONE"],
    },
    {
        "sequence":   50,
        "name": "Blending",
        "step_type": "production",
        "work_cell_code": "WC-BLEND",
        "expected_cycle_time_sec": 900.0,
        "erp_operation_number": "0050",
        "input_disposition_codes": ["P-MILL-DONE"],
        "output_disposition_codes": ["P-BLEND-DONE"],
    },
    {
        "sequence":   60,
        "name": "Tablet Compression",
        "step_type": "production",
        "work_cell_code": "WC-PRESS",
        "expected_cycle_time_sec": 3600.0,
        "erp_operation_number": "0060",
        # Accepts fresh blend OR re-milled rework from step 110
        "input_disposition_codes": ["P-BLEND-DONE", "P-REWORK-DONE"],
        "output_disposition_codes": ["P-COMP-DONE"],
    },
    {
        "sequence":   70,
        "name": "In-Process Control (IPC)",
        "step_type": "inspection",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 900.0,
        "erp_operation_number": "0070",
        "input_disposition_codes": ["P-COMP-DONE"],
        "output_disposition_codes": ["P-IPC-PASS", "P-IPC-FAIL", "P-ESCALATE"],
    },
    {
        "sequence":   80,
        "name": "Film Coating",
        "step_type": "production",
        "work_cell_code": "WC-COAT",
        "expected_cycle_time_sec": 7200.0,
        "erp_operation_number": "0080",
        # Standard path (IPC-PASS) or MRB approved deviation (MRB-USE-AS-IS)
        "input_disposition_codes": ["P-IPC-PASS", "P-MRB-USE-AS-IS"],
        "output_disposition_codes": ["P-COAT-DONE"],
    },
    {
        "sequence":   90,
        "name": "QC Release Testing",
        "step_type": "inspection",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 7200.0,
        "erp_operation_number": "0090",
        "input_disposition_codes": ["P-COAT-DONE"],
        "output_disposition_codes": ["P-REL-PASS", "P-REL-FAIL"],
    },
    {
        "sequence":  100,
        "name": "Blister Packaging",
        "step_type": "production",
        "work_cell_code": "WC-PACK",
        "expected_cycle_time_sec": 1800.0,
        "erp_operation_number": "0100",
        "input_disposition_codes": ["P-REL-PASS"],
        "output_disposition_codes": [],            # terminal — batch complete
    },
    {
        "sequence":  110,
        "name": "Tablet Rework",
        "step_type": "rework",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 2400.0,
        "erp_operation_number": "0110",
        # Fed by IPC failure OR MRB reprocess decision
        "input_disposition_codes": ["P-IPC-FAIL", "P-MRB-REPROCESS"],
        "output_disposition_codes": ["P-REWORK-DONE"],
    },
    {
        "sequence":  120,
        "name": "MRB Review",
        "step_type": "mrb",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 3600.0,
        "erp_operation_number": "0120",
        "input_disposition_codes": ["P-ESCALATE", "P-REL-FAIL"],
        "output_disposition_codes": ["P-MRB-REPROCESS", "P-MRB-USE-AS-IS"],
    },
]

# ---------------------------------------------------------------------------
# Step Parameters  (recipe / specification targets — CPP/CQA per ICH Q8)
# ---------------------------------------------------------------------------

STEP_PARAMS: dict[int, list[dict]] = {
    # Step 10 (Dispensing) has no recipe-level parameters: the two dispensing
    # checks ("Balance Accuracy Verified", "Yield Reconciliation") are
    # procedural execution checks defined solely as DATA_DEFS so that
    # DataDefinition codes (PHX-DSP-BAL / PHX-DSP-YLD) remain the single
    # source of truth for EBR traceability — see electronics_data.py note.
    20: [  # Wet Granulation
        {"name": "Impeller Speed",   "data_type": "numeric", "target_value": "400",  "lower_limit": "350",  "upper_limit": "450",  "uom": "RPM", "is_required": True},
        {"name": "Chopper Speed",    "data_type": "numeric", "target_value": "3000", "lower_limit": "2800", "upper_limit": "3200", "uom": "RPM", "is_required": True},
        {"name": "Granulation Time", "data_type": "numeric", "target_value": "10",   "lower_limit": "8",    "upper_limit": "12",   "uom": "min", "is_required": True},
        {"name": "End-Point LOD",    "data_type": "numeric", "target_value": "25.0", "lower_limit": "22.0", "upper_limit": "28.0", "uom": "%",   "is_required": True},
    ],
    30: [  # Fluid Bed Drying
        {"name": "Inlet Air Temperature",  "data_type": "numeric", "target_value": "65",  "lower_limit": "60",  "upper_limit": "70",  "uom": "°C",  "is_required": True},
        {"name": "Outlet Air Temperature", "data_type": "numeric", "target_value": "42",  "lower_limit": "38",  "upper_limit": "46",  "uom": "°C",  "is_required": True},
        {"name": "Final LOD",              "data_type": "numeric", "target_value": "1.5", "lower_limit": "1.0", "upper_limit": "2.0", "uom": "%",   "is_required": True},
        {"name": "Drying Time",            "data_type": "numeric", "target_value": "30",  "lower_limit": "20",  "upper_limit": "45",  "uom": "min", "is_required": True},
    ],
    40: [  # Milling
        {"name": "Screen Size",  "data_type": "numeric", "target_value": "1.0", "lower_limit": "0.8", "upper_limit": "1.2", "uom": "mm",  "is_required": True},
        {"name": "Mill Speed",   "data_type": "numeric", "target_value": "750", "lower_limit": "600", "upper_limit": "900", "uom": "RPM", "is_required": True},
        {"name": "D50 Particle Size", "data_type": "numeric", "target_value": "250", "lower_limit": "150", "upper_limit": "350", "uom": "µm",  "is_required": True},
    ],
    50: [  # Blending
        {"name": "Blend Time",  "data_type": "numeric", "target_value": "20",  "lower_limit": "18",  "upper_limit": "25",  "uom": "min", "is_required": True},
        {"name": "Blender Speed", "data_type": "numeric", "target_value": "12",  "lower_limit": "10",  "upper_limit": "15",  "uom": "RPM", "is_required": True},
        {"name": "Content Uniformity %RSD", "data_type": "numeric", "target_value": "2.0", "lower_limit": "0.0", "upper_limit": "5.0", "uom": "%",   "is_required": True},
    ],
    60: [  # Tablet Compression
        {"name": "Main Compression Force", "data_type": "numeric", "target_value": "15000", "lower_limit": "10000", "upper_limit": "20000", "uom": "N",  "is_required": True},
        {"name": "Pre-Compression Force",  "data_type": "numeric", "target_value": "2000",  "lower_limit": "1000",  "upper_limit": "3000",  "uom": "N",  "is_required": True},
        {"name": "Turret Speed",           "data_type": "numeric", "target_value": "25",    "lower_limit": "15",    "upper_limit": "35",    "uom": "RPM","is_required": True},
        {"name": "Tablet Weight",          "data_type": "numeric", "target_value": "300",   "lower_limit": "285",   "upper_limit": "315",   "uom": "mg", "is_required": True},
        {"name": "Tablet Hardness",        "data_type": "numeric", "target_value": "80",    "lower_limit": "60",    "upper_limit": "100",   "uom": "N",  "is_required": True},
        {"name": "Tablet Thickness",       "data_type": "numeric", "target_value": "4.5",   "lower_limit": "4.3",   "upper_limit": "4.7",   "uom": "mm", "is_required": True},
    ],
    70: [  # IPC Check
        {"name": "Tablet Weight (IPC)",    "data_type": "numeric", "target_value": "300",   "lower_limit": "285",   "upper_limit": "315",   "uom": "mg",  "is_required": True},
        {"name": "Tablet Hardness (IPC)",  "data_type": "numeric", "target_value": "80",    "lower_limit": "60",    "upper_limit": "100",   "uom": "N",   "is_required": True},
        {"name": "Friability",             "data_type": "numeric", "target_value": "0.1",   "lower_limit": "0.0",   "upper_limit": "0.5",   "uom": "%",   "is_required": True},
        {"name": "Disintegration Time",    "data_type": "numeric", "target_value": "5",     "lower_limit": "0",     "upper_limit": "15",    "uom": "min", "is_required": True},
        # "Appearance Approved" is a subjective visual check → DATA_DEFS only (PHX-IPC-APP)
    ],
    80: [  # Film Coating
        {"name": "Coating Pan Speed",      "data_type": "numeric", "target_value": "5",    "lower_limit": "3",    "upper_limit": "8",    "uom": "RPM", "is_required": True},
        {"name": "Inlet Air Temperature",  "data_type": "numeric", "target_value": "60",   "lower_limit": "55",   "upper_limit": "65",   "uom": "°C",  "is_required": True},
        {"name": "Outlet Air Temperature", "data_type": "numeric", "target_value": "42",   "lower_limit": "38",   "upper_limit": "46",   "uom": "°C",  "is_required": True},
        {"name": "Weight Gain",            "data_type": "numeric", "target_value": "3.0",  "lower_limit": "2.5",  "upper_limit": "3.5",  "uom": "%",   "is_required": True},
        # "Coating Appearance" is a visual inspection check → DATA_DEFS only (PHX-COT-APP)
    ],
    90: [  # QC Release Testing
        {"name": "Assay (% label claim)",  "data_type": "numeric", "target_value": "100.0","lower_limit": "95.0",  "upper_limit": "105.0", "uom": "%",  "is_required": True},
        {"name": "Dissolution Q at 45 min", "data_type": "numeric", "target_value": "85.0","lower_limit": "70.0","upper_limit": "110.0","uom": "%",   "is_required": True},
        {"name": "Content Uniformity",     "data_type": "numeric", "target_value": "100.0","lower_limit": "85.0",  "upper_limit": "115.0", "uom": "%",  "is_required": True},
        {"name": "Related Substances",     "data_type": "numeric", "target_value": "0.0",  "lower_limit": "0.0",   "upper_limit": "0.5",   "uom": "%",  "is_required": True},
        {"name": "Water Activity",         "data_type": "numeric", "target_value": "0.4",  "lower_limit": "0.0",   "upper_limit": "0.6",   "uom": None, "is_required": True},
        {"name": "Microbial Count",        "data_type": "numeric", "target_value": "0",    "lower_limit": "0",     "upper_limit": "100",   "uom": "CFU/g", "is_required": True},
    ],
    100: [  # Blister Packaging
        # Seal Integrity, Print Verification, Serialisation are pass/fail
        # execution checks → DATA_DEFS only (PHX-PKG-SEAL/PRN/SER).
        # Only Label Reconciliation has a quantitative recipe specification.
        {"name": "Label Reconciliation",   "data_type": "numeric", "target_value": "1667", "lower_limit": "1667","upper_limit": "1667","uom": "EA", "is_required": True},
    ],
    # Steps 110 (Tablet Rework) and 120 (MRB Review) have no recipe-level
    # parameters: every field is free-form operator documentation or an
    # administrative classification with no defined target/limits.
    # All entries live solely in DATA_DEFS — same rationale as step 10.
}

# ---------------------------------------------------------------------------
# Data Collection Definitions  (actual measurements per step)
# ---------------------------------------------------------------------------

DATA_DEFS: dict[int, list[dict]] = {
    10: [  # Dispensing
        {"code": "PHX-DSP-BAL",  "name": "Balance Accuracy Verified", "data_type": "boolean", "source": "manual",    "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
        {"code": "PHX-DSP-YLD",  "name": "Yield Reconciliation",      "data_type": "numeric", "source": "manual",    "lower_limit": 99.5,   "upper_limit": 100.5,  "uom": "%",   "is_required": True},
    ],
    20: [  # Wet Granulation
        {"code": "PHX-GRN-IMPS", "name": "Impeller Speed",            "data_type": "numeric", "source": "equipment", "lower_limit": 350.0,  "upper_limit": 450.0,  "uom": "RPM", "is_required": True},
        {"code": "PHX-GRN-CHOP", "name": "Chopper Speed",             "data_type": "numeric", "source": "equipment", "lower_limit": 2800.0, "upper_limit": 3200.0, "uom": "RPM", "is_required": True},
        {"code": "PHX-GRN-TIME", "name": "Granulation Time",          "data_type": "numeric", "source": "equipment", "lower_limit": 8.0,    "upper_limit": 12.0,   "uom": "min", "is_required": True},
        {"code": "PHX-GRN-LOD",  "name": "End-Point LOD",             "data_type": "numeric", "source": "equipment", "lower_limit": 22.0,   "upper_limit": 28.0,   "uom": "%",   "is_required": True},
    ],
    30: [  # Fluid Bed Drying
        {"code": "PHX-DRY-INLT", "name": "Inlet Air Temperature",     "data_type": "numeric", "source": "equipment", "lower_limit": 60.0,   "upper_limit": 70.0,   "uom": "°C",  "is_required": True},
        {"code": "PHX-DRY-OUTL", "name": "Outlet Air Temperature",    "data_type": "numeric", "source": "equipment", "lower_limit": 38.0,   "upper_limit": 46.0,   "uom": "°C",  "is_required": True},
        {"code": "PHX-DRY-LOD",  "name": "Final LOD",                 "data_type": "numeric", "source": "equipment", "lower_limit": 1.0,    "upper_limit": 2.0,    "uom": "%",   "is_required": True},
        {"code": "PHX-DRY-TIME", "name": "Drying Time",               "data_type": "numeric", "source": "equipment", "lower_limit": 20.0,   "upper_limit": 45.0,   "uom": "min", "is_required": True},
    ],
    40: [  # Milling
        {"code": "PHX-MLL-SCR",  "name": "Screen Size",               "data_type": "numeric", "source": "manual",    "lower_limit": 0.8,    "upper_limit": 1.2,    "uom": "mm",  "is_required": True},
        {"code": "PHX-MLL-SPD",  "name": "Mill Speed",                "data_type": "numeric", "source": "equipment", "lower_limit": 600.0,  "upper_limit": 900.0,  "uom": "RPM", "is_required": True},
        {"code": "PHX-MLL-D50",  "name": "D50 Particle Size",         "data_type": "numeric", "source": "equipment", "lower_limit": 150.0,  "upper_limit": 350.0,  "uom": "µm",  "is_required": True},
    ],
    50: [  # Blending
        {"code": "PHX-BLD-TIME", "name": "Blend Time",                "data_type": "numeric", "source": "equipment", "lower_limit": 18.0,   "upper_limit": 25.0,   "uom": "min", "is_required": True},
        {"code": "PHX-BLD-RPM",  "name": "Blender Speed",             "data_type": "numeric", "source": "equipment", "lower_limit": 10.0,   "upper_limit": 15.0,   "uom": "RPM", "is_required": True},
        {"code": "PHX-BLD-CU",   "name": "Content Uniformity %RSD",   "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,    "upper_limit": 5.0,    "uom": "%",   "is_required": True},
    ],
    60: [  # Tablet Compression
        {"code": "PHX-CMP-MCF",  "name": "Main Compression Force",    "data_type": "numeric", "source": "equipment", "lower_limit": 10000.0,"upper_limit": 20000.0,"uom": "N",   "is_required": True},
        {"code": "PHX-CMP-PCF",  "name": "Pre-Compression Force",     "data_type": "numeric", "source": "equipment", "lower_limit": 1000.0, "upper_limit": 3000.0, "uom": "N",   "is_required": True},
        {"code": "PHX-CMP-TRP",  "name": "Turret Speed",              "data_type": "numeric", "source": "equipment", "lower_limit": 15.0,   "upper_limit": 35.0,   "uom": "RPM", "is_required": True},
        {"code": "PHX-CMP-WGT",  "name": "Tablet Weight",             "data_type": "numeric", "source": "equipment", "lower_limit": 285.0,  "upper_limit": 315.0,  "uom": "mg",  "is_required": True},
        {"code": "PHX-CMP-HRD",  "name": "Tablet Hardness",           "data_type": "numeric", "source": "equipment", "lower_limit": 60.0,   "upper_limit": 100.0,  "uom": "N",   "is_required": True},
        {"code": "PHX-CMP-THK",  "name": "Tablet Thickness",          "data_type": "numeric", "source": "equipment", "lower_limit": 4.3,    "upper_limit": 4.7,    "uom": "mm",  "is_required": True},
    ],
    70: [  # IPC Check
        {"code": "PHX-IPC-WGT",  "name": "Tablet Weight (IPC)",       "data_type": "numeric", "source": "equipment", "lower_limit": 285.0,  "upper_limit": 315.0,  "uom": "mg",  "is_required": True},
        {"code": "PHX-IPC-HRD",  "name": "Tablet Hardness (IPC)",     "data_type": "numeric", "source": "equipment", "lower_limit": 60.0,   "upper_limit": 100.0,  "uom": "N",   "is_required": True},
        {"code": "PHX-IPC-FRI",  "name": "Friability",                "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,    "upper_limit": 0.5,    "uom": "%",   "is_required": True},
        {"code": "PHX-IPC-DIS",  "name": "Disintegration Time",       "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,    "upper_limit": 15.0,   "uom": "min", "is_required": True},
        {"code": "PHX-IPC-APP",  "name": "Appearance Approved",       "data_type": "boolean", "source": "manual",    "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
    ],
    80: [  # Film Coating
        {"code": "PHX-COT-PSPD", "name": "Coating Pan Speed",         "data_type": "numeric", "source": "equipment", "lower_limit": 3.0,    "upper_limit": 8.0,    "uom": "RPM", "is_required": True},
        {"code": "PHX-COT-INLT", "name": "Inlet Air Temperature",     "data_type": "numeric", "source": "equipment", "lower_limit": 55.0,   "upper_limit": 65.0,   "uom": "°C",  "is_required": True},
        {"code": "PHX-COT-OUTL", "name": "Outlet Air Temperature",    "data_type": "numeric", "source": "equipment", "lower_limit": 38.0,   "upper_limit": 46.0,   "uom": "°C",  "is_required": True},
        {"code": "PHX-COT-WGT",  "name": "Weight Gain",               "data_type": "numeric", "source": "equipment", "lower_limit": 2.5,    "upper_limit": 3.5,    "uom": "%",   "is_required": True},
        {"code": "PHX-COT-APP",  "name": "Coating Appearance",        "data_type": "boolean", "source": "manual",    "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
    ],
    90: [  # QC Release Testing
        {"code": "PHX-REL-ASY",  "name": "Assay (% label claim)",     "data_type": "numeric", "source": "equipment", "lower_limit": 95.0,   "upper_limit": 105.0,  "uom": "%",      "is_required": True},
        {"code": "PHX-REL-DSL",  "name": "Dissolution Q at 45 min",   "data_type": "numeric", "source": "equipment", "lower_limit": 70.0,   "upper_limit": 110.0,  "uom": "%",      "is_required": True},
        {"code": "PHX-REL-CU",   "name": "Content Uniformity",        "data_type": "numeric", "source": "equipment", "lower_limit": 85.0,   "upper_limit": 115.0,  "uom": "%",      "is_required": True},
        {"code": "PHX-REL-RS",   "name": "Related Substances",        "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,    "upper_limit": 0.5,    "uom": "%",      "is_required": True},
        {"code": "PHX-REL-WA",   "name": "Water Activity",            "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,    "upper_limit": 0.6,    "uom": None,     "is_required": True},
        {"code": "PHX-REL-MCB",  "name": "Microbial Count",           "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,    "upper_limit": 100.0,  "uom": "CFU/g",  "is_required": True},
    ],
    100: [  # Blister Packaging
        {"code": "PHX-PKG-SEAL", "name": "Seal Integrity Passed",     "data_type": "boolean", "source": "equipment", "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"code": "PHX-PKG-PRN",  "name": "Print Verification OK",     "data_type": "boolean", "source": "equipment", "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"code": "PHX-PKG-LBL",  "name": "Label Reconciliation",      "data_type": "numeric", "source": "manual",    "lower_limit": 1667.0,"upper_limit": 1667.0,"uom": "EA","is_required": True},
        {"code": "PHX-PKG-SER",  "name": "Serialisation Verified",    "data_type": "boolean", "source": "equipment", "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
    ],
    110: [  # Tablet Rework
        {"code": "PHX-RWK-ACT",  "name": "Rework Action",             "data_type": "enum",    "source": "manual",    "lower_limit": None, "upper_limit": None,  "uom": None, "is_required": True},
        {"code": "PHX-RWK-NTS",  "name": "Rework Notes",              "data_type": "string",  "source": "manual",    "lower_limit": None, "upper_limit": None,  "uom": None, "is_required": True},
        {"code": "PHX-RWK-YLD",  "name": "Yield After Rework",        "data_type": "numeric", "source": "manual",    "lower_limit": 95.0, "upper_limit": None,  "uom": "%",  "is_required": True},
    ],
    120: [  # MRB Review
        {"code": "PHX-MRB-CAT",  "name": "Deviation Category",        "data_type": "enum",    "source": "manual",    "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"code": "PHX-MRB-IMP",  "name": "Impact Assessment",         "data_type": "string",  "source": "manual",    "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"code": "PHX-MRB-DSP",  "name": "Disposition Decision",      "data_type": "enum",    "source": "manual",    "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"code": "PHX-MRB-NTS",  "name": "Review Notes",              "data_type": "string",  "source": "manual",    "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
    ],
}

# ---------------------------------------------------------------------------
# Quality Tests
# ---------------------------------------------------------------------------

QUALITY_TEST: dict = {
    "code": "PHX-REL-TEST",
    "name": "Tablet Batch Release Test",
    "test_type": "offline",
    "description": (
        "Full batch-release analytical testing per ICH Q6A: assay, dissolution, "
        "content uniformity, related substances, water activity, microbiology"
    ),
    "step_sequence": 90,
    "parameters": {},
}

# ---------------------------------------------------------------------------
# Production Orders  (create via ERP Simulator — empty here)
# ---------------------------------------------------------------------------

ORDERS: list[dict] = []

# ---------------------------------------------------------------------------
# Physical Model  (ISA-95 hierarchy)
# ---------------------------------------------------------------------------

SITE = {
    "code": "PHX-PHARMA",
    "name": "Phoenix Pharmaceutical",
    "description": "Solid-dose pharmaceutical manufacturing facility (cGMP, 21 CFR Part 211)",
    "timezone": "America/Phoenix",
}
AREA = {
    "code": "PHX-SOLID",
    "name": "Solid Dose Manufacturing",
    "description": "Tablet granulation, compression, film coating, and packaging area",
}
LINE = {
    "code": "PHX-LINE-01",
    "name": "Tablet Manufacturing Line 1",
    "description": "Wet granulation → film-coated tablet → blister pack line (50 000 tab/batch)",
}

WORK_CELLS: list[dict] = [
    {"code": "WC-DISP",   "name": "Dispensing Suite",            "description": "Controlled-environment weighing & dispensing; laminar-flow hood"},
    {"code": "WC-GRAN",   "name": "Granulation Suite",           "description": "High-shear wet granulation"},
    {"code": "WC-DRY",    "name": "Drying Suite",                "description": "Fluid-bed granule drying"},
    {"code": "WC-MILL",   "name": "Milling Suite",               "description": "Granule size-reduction (cone mill)"},
    {"code": "WC-BLEND",  "name": "Blending Suite",              "description": "Bin blending with lubrication step"},
    {"code": "WC-PRESS",  "name": "Compression Suite",           "description": "Rotary tablet press; dual presses for dispatch demonstration"},
    {"code": "WC-COAT",   "name": "Film Coating Suite",          "description": "Pan coater for aqueous film coating"},
    {"code": "WC-QC",     "name": "QC Laboratory",               "description": "HPLC, dissolution, hardness, IPC and release-test instruments"},
    {"code": "WC-PACK",   "name": "Packaging Suite",             "description": "Thermoform-fill-seal blister packer; carton insert; serialisation"},
    {"code": "WC-REWORK", "name": "MRB / Rework Area",           "description": "Material review board bench and tablet rework operations"},
]

EQUIPMENT: list[dict] = [
    # Dispensing
    {"code": "DISP-001",    "name": "Dispensing Booth DISP-001",      "work_cell_code": "WC-DISP",   "state_model": "semi_e10", "max_queue_depth": 1},
    # Granulation
    {"code": "HSG-001",     "name": "High-Shear Granulator HSG-001",  "work_cell_code": "WC-GRAN",   "state_model": "semi_e10", "max_queue_depth": 1},
    # Drying
    {"code": "FBD-001",     "name": "Fluid Bed Dryer FBD-001",        "work_cell_code": "WC-DRY",    "state_model": "semi_e10", "max_queue_depth": 1},
    # Milling
    {"code": "MILL-001",    "name": "Cone Mill MILL-001",              "work_cell_code": "WC-MILL",   "state_model": "packml",   "max_queue_depth": 2},
    # Blending — dual bin blenders for dispatch demonstration
    {"code": "BLEND-001",   "name": "Bin Blender BLEND-001",          "work_cell_code": "WC-BLEND",  "state_model": "semi_e10", "max_queue_depth": 1},
    {"code": "BLEND-002",   "name": "Bin Blender BLEND-002",          "work_cell_code": "WC-BLEND",  "state_model": "semi_e10", "max_queue_depth": 1},
    # Tablet presses — dual presses for dispatch demonstration
    {"code": "PRESS-001",   "name": "Tablet Press PRESS-001",         "work_cell_code": "WC-PRESS",  "state_model": "packml",   "max_queue_depth": 2},
    {"code": "PRESS-002",   "name": "Tablet Press PRESS-002",         "work_cell_code": "WC-PRESS",  "state_model": "packml",   "max_queue_depth": 2},
    # Film coating
    {"code": "COATER-001",  "name": "Film Coater FC-001",              "work_cell_code": "WC-COAT",   "state_model": "semi_e10", "max_queue_depth": 1},
    # QC laboratory (handles IPC, release testing, MRB review)
    {"code": "QCLAB-001",   "name": "QC Analytical Suite QCLAB-001",  "work_cell_code": "WC-QC",     "state_model": "semi_e10", "max_queue_depth": 5},
    # Packaging
    {"code": "BPAK-001",    "name": "Blister Packer BP-001",          "work_cell_code": "WC-PACK",   "state_model": "packml",   "max_queue_depth": 2},
    # MRB / Rework
    {"code": "REWORK-001",  "name": "MRB / Rework Bench RW-001",      "work_cell_code": "WC-REWORK", "state_model": "semi_e10", "max_queue_depth": 3},
]

# Equipment–material assignments  (design speed in tablets/h, target OEE %)
EQUIPMENT_MATERIALS: list[dict] = [
    {"equipment_code": "DISP-001",   "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 95.0},
    {"equipment_code": "HSG-001",    "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 90.0},
    {"equipment_code": "FBD-001",    "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "MILL-001",   "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 93.0},
    {"equipment_code": "BLEND-001",  "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "BLEND-002",  "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "PRESS-001",  "material_code": "FG-IBU-200MG", "design_speed": 90000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 88.0},
    {"equipment_code": "PRESS-002",  "material_code": "FG-IBU-200MG", "design_speed": 90000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 88.0},
    {"equipment_code": "COATER-001", "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 90.0},
    {"equipment_code": "QCLAB-001",  "material_code": "FG-IBU-200MG", "design_speed": 50000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 95.0},
    {"equipment_code": "BPAK-001",   "material_code": "FG-IBU-200MG", "design_speed": 54000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 88.0},
    {"equipment_code": "REWORK-001", "material_code": "FG-IBU-200MG", "design_speed": 10000.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 70.0},
]

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Equipment Classes & Properties
# ---------------------------------------------------------------------------

EQUIPMENT_CLASSES: list[dict] = [
    {"code": "DISPENSING_BOOTH", "name": "Dispensing Suite",         "description": "Controlled-environment weighing & dispensing booth"},
    {"code": "GRANULATOR",       "name": "High-Shear Granulator",    "description": "Wet / dry granulation equipment (top-drive or bottom-drive)"},
    {"code": "FLUID_BED_DRYER",  "name": "Fluid Bed Dryer",          "description": "Fluidised-bed drying for pharmaceutical granules"},
    {"code": "SIZE_MILL",        "name": "Size-Reduction Mill",      "description": "Cone mill, oscillating granulator, or co-mill"},
    {"code": "BIN_BLENDER",      "name": "Bin Blender",              "description": "IBC bin blender or V-blender for powder/granule blending"},
    {"code": "TABLET_PRESS",     "name": "Rotary Tablet Press",      "description": "Multi-punch rotary compression machine"},
    {"code": "FILM_COATER",      "name": "Film Coating Pan",         "description": "Perforated pan or drum coater for aqueous film coating"},
    {"code": "PHARMA_ANALYZER",  "name": "QC Analytical Suite",      "description": "HPLC, dissolution tester, hardness / friability tester"},
    {"code": "BLISTER_PACKER",   "name": "Blister Packaging Machine","description": "Thermoform-fill-seal blister packaging line"},
    {"code": "MRB_STATION",      "name": "MRB / Rework Station",     "description": "Material review board and tablet rework / re-milling bench"},
]

EQUIPMENT_CLASS_PROPERTIES: list[dict] = [
    # Dispensing Booth
    {"class_code": "DISPENSING_BOOTH", "name": "max_batch_size_kg",    "data_type": "float", "uom_id": "kg",  "default_value": "200",  "description": "Maximum dispensable batch size"},
    {"class_code": "DISPENSING_BOOTH", "name": "balance_readability_g","data_type": "float", "uom_id": "g",   "default_value": "0.1",  "description": "Balance readability / resolution"},
    # Granulator
    {"class_code": "GRANULATOR",       "name": "bowl_volume_l",        "data_type": "float", "uom_id": "L",   "default_value": "150",  "description": "Granulator bowl volume"},
    {"class_code": "GRANULATOR",       "name": "max_impeller_rpm",     "data_type": "float", "uom_id": "RPM", "default_value": "500",  "description": "Maximum impeller speed"},
    # Fluid Bed Dryer
    {"class_code": "FLUID_BED_DRYER",  "name": "max_inlet_temp_c",     "data_type": "float", "uom_id": "°C",  "default_value": "90",   "description": "Maximum inlet air temperature"},
    {"class_code": "FLUID_BED_DRYER",  "name": "bowl_volume_l",        "data_type": "float", "uom_id": "L",   "default_value": "300",  "description": "Fluidising bowl volume"},
    # Tablet Press
    {"class_code": "TABLET_PRESS",     "name": "max_compression_n",    "data_type": "float", "uom_id": "N",   "default_value": "40000","description": "Maximum main compression force"},
    {"class_code": "TABLET_PRESS",     "name": "max_turret_rpm",       "data_type": "float", "uom_id": "RPM", "default_value": "60",   "description": "Maximum turret speed"},
    {"class_code": "TABLET_PRESS",     "name": "punch_count",          "data_type": "int",   "uom_id": None,  "default_value": "36",   "description": "Number of punches / stations"},
    # Film Coater
    {"class_code": "FILM_COATER",      "name": "pan_volume_l",         "data_type": "float", "uom_id": "L",   "default_value": "60",   "description": "Coating pan volume"},
    {"class_code": "FILM_COATER",      "name": "max_load_kg",          "data_type": "float", "uom_id": "kg",  "default_value": "40",   "description": "Maximum tablet-bed load"},
    # Blister Packer
    {"class_code": "BLISTER_PACKER",   "name": "max_strokes_per_min",  "data_type": "float", "uom_id": None,  "default_value": "60",   "description": "Maximum forming strokes per minute"},
    {"class_code": "BLISTER_PACKER",   "name": "max_blister_width_mm", "data_type": "float", "uom_id": "mm",  "default_value": "130",  "description": "Maximum blister web width"},
    # Bin Blender
    {"class_code": "BIN_BLENDER",      "name": "bin_volume_l",         "data_type": "float", "uom_id": "L",   "default_value": "500",  "description": "Bin IBC volume"},
]

# Maps equipment code → equipment class code
EQUIPMENT_CLASS_MAP: dict[str, str] = {
    "DISP-001":   "DISPENSING_BOOTH",
    "HSG-001":    "GRANULATOR",
    "FBD-001":    "FLUID_BED_DRYER",
    "MILL-001":   "SIZE_MILL",
    "BLEND-001":  "BIN_BLENDER",
    "BLEND-002":  "BIN_BLENDER",
    "PRESS-001":  "TABLET_PRESS",
    "PRESS-002":  "TABLET_PRESS",
    "COATER-001": "FILM_COATER",
    "QCLAB-001":  "PHARMA_ANALYZER",
    "BPAK-001":   "BLISTER_PACKER",
    "REWORK-001": "MRB_STATION",
}

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Process Segment → Equipment Class (dispatch constraint)
# ---------------------------------------------------------------------------
# Each process segment declares what class of equipment it needs; the
# dispatcher narrows the candidate set before applying
# SegmentEquipmentRequirement preferences below.

STEP_EQUIPMENT_CLASS: dict[int, str] = {
    10:  "DISPENSING_BOOTH",  # Dispensing
    20:  "GRANULATOR",        # Wet Granulation
    30:  "FLUID_BED_DRYER",   # Fluid Bed Drying
    40:  "SIZE_MILL",         # Milling
    50:  "BIN_BLENDER",       # Blending
    60:  "TABLET_PRESS",      # Tablet Compression (dual presses → dispatch)
    70:  "PHARMA_ANALYZER",   # IPC Check
    80:  "FILM_COATER",       # Film Coating
    90:  "PHARMA_ANALYZER",   # QC Release Testing
    100: "BLISTER_PACKER",    # Blister Packaging
    110: "MRB_STATION",       # Tablet Rework
    120: "MRB_STATION",       # MRB Review
}

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Segment Equipment Requirements
# ---------------------------------------------------------------------------
# Specific-equipment preferences augmenting the class-level constraint.
# use_type: "required" | "preferred" | "alternate"

SEGMENT_EQUIPMENT_REQUIREMENTS: list[dict] = [
    # Dispensing — single certified booth; must use it
    {"step_sequence": 10,  "equipment_code": "DISP-001",   "use_type": "required",   "description": "Certified cGMP dispensing booth"},
    # Granulation — single HSG unit
    {"step_sequence": 20,  "equipment_code": "HSG-001",    "use_type": "required",   "description": "High-shear granulator"},
    # Drying — single FBD unit
    {"step_sequence": 30,  "equipment_code": "FBD-001",    "use_type": "required",   "description": "Fluid bed dryer"},
    # Milling — single cone mill
    {"step_sequence": 40,  "equipment_code": "MILL-001",   "use_type": "required",   "description": "Cone mill"},
    # Blending — dual blenders (dispatch demo: either BLEND-001 or BLEND-002)
    {"step_sequence": 50,  "equipment_code": "BLEND-001",  "use_type": "preferred",  "description": "Primary bin blender"},
    {"step_sequence": 50,  "equipment_code": "BLEND-002",  "use_type": "alternate",  "description": "Secondary bin blender (load balancing)"},
    # Compression — dual presses (dispatch demo: either PRESS-001 or PRESS-002)
    {"step_sequence": 60,  "equipment_code": "PRESS-001",  "use_type": "preferred",  "description": "Primary tablet press"},
    {"step_sequence": 60,  "equipment_code": "PRESS-002",  "use_type": "alternate",  "description": "Secondary tablet press (load balancing)"},
    # Film coating — single pan coater
    {"step_sequence": 80,  "equipment_code": "COATER-001", "use_type": "required",   "description": "Film coating pan"},
    # QC (IPC, release, MRB) all share the single QC analytical suite
    {"step_sequence": 70,  "equipment_code": "QCLAB-001",  "use_type": "required",   "description": "QC analytical suite (IPC)"},
    {"step_sequence": 90,  "equipment_code": "QCLAB-001",  "use_type": "required",   "description": "QC analytical suite (release test)"},
    {"step_sequence": 120, "equipment_code": "QCLAB-001",  "use_type": "required",   "description": "QC analytical suite (MRB review)"},
    # Packaging
    {"step_sequence": 100, "equipment_code": "BPAK-001",   "use_type": "required",   "description": "Blister packer"},
    # Rework and MRB share the bench
    {"step_sequence": 110, "equipment_code": "REWORK-001", "use_type": "required",   "description": "MRB / rework bench"},
    {"step_sequence": 120, "equipment_code": "REWORK-001", "use_type": "required",   "description": "MRB / rework bench"},
]

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Segment Material Requirements
# ---------------------------------------------------------------------------
# Declarative per-segment consumed/produced materials for dispatch and
# genealogy tracking (independent of any specific product BOM).

SEGMENT_MATERIAL_REQUIREMENTS: list[dict] = [
    # 10 — Dispensing: API and all excipients consumed
    {"step_sequence": 10, "material_code": "RM-API-IBU",   "quantity": 10.0,   "uom": "kg",  "material_use": "consumed", "position": 10, "description": "Active pharmaceutical ingredient"},
    {"step_sequence": 10, "material_code": "RM-EXC-MCC",   "quantity": 3.05,   "uom": "kg",  "material_use": "consumed", "position": 20, "description": "Filler / diluent"},
    {"step_sequence": 10, "material_code": "RM-EXC-CCS",   "quantity": 0.625,  "uom": "kg",  "material_use": "consumed", "position": 30, "description": "Disintegrant"},
    {"step_sequence": 10, "material_code": "RM-EXC-PVP",   "quantity": 0.625,  "uom": "kg",  "material_use": "consumed", "position": 40, "description": "Binder"},
    {"step_sequence": 10, "material_code": "RM-EXC-MGST",  "quantity": 0.2,    "uom": "kg",  "material_use": "consumed", "position": 50, "description": "Lubricant"},
    # 20 — Granulation: purified water consumed; granule blend produced
    {"step_sequence": 20, "material_code": "RM-WATER-PW",  "quantity": 0.5,    "uom": "L",   "material_use": "consumed", "position": 10, "description": "Binder solution water"},
    {"step_sequence": 20, "material_code": "SF-GRANULE",   "quantity": 14.5,   "uom": "kg",  "material_use": "produced", "position": 20, "description": "Wet granule intermediate"},
    # 60 — Compression: uncoated tablet cores produced
    {"step_sequence": 60, "material_code": "SF-TABLET-UC", "quantity": 50000.0,"uom": "EA",  "material_use": "produced", "position": 10, "description": "Uncoated tablet core"},
    # 80 — Film Coating: coating material consumed; FG tablet assigned on pass
    {"step_sequence": 80, "material_code": "RM-COAT-OPW",  "quantity": 0.45,   "uom": "kg",  "material_use": "consumed", "position": 10, "description": "Aqueous film coat dispersion"},
    {"step_sequence": 80, "material_code": "FG-IBU-200MG", "quantity": 50000.0,"uom": "EA",  "material_use": "produced", "position": 20, "description": "Film-coated tablet (FG status pending release)"},
    # 100 — Packaging: all primary packaging consumed
    {"step_sequence": 100, "material_code": "PKG-BLISTER", "quantity": 16.7,   "uom": "m",   "material_use": "consumed", "position": 10, "description": "Blister PVC base film"},
    {"step_sequence": 100, "material_code": "PKG-LIDDING", "quantity": 16.7,   "uom": "m",   "material_use": "consumed", "position": 20, "description": "Blister aluminium lidding"},
    {"step_sequence": 100, "material_code": "PKG-CARTON",  "quantity": 1667.0, "uom": "EA",  "material_use": "consumed", "position": 30, "description": "30-pack folding carton"},
    {"step_sequence": 100, "material_code": "PKG-INSERT",  "quantity": 1667.0, "uom": "EA",  "material_use": "consumed", "position": 40, "description": "Package insert leaflet"},
    {"step_sequence": 100, "material_code": "PKG-SEAL",    "quantity": 1667.0, "uom": "EA",  "material_use": "consumed", "position": 50, "description": "Tamper-evident carton seal"},
]

# ---------------------------------------------------------------------------
# OperationsDefinition ↔ Material assignments (route-level materials)
# ---------------------------------------------------------------------------

ROUTE_MATERIAL_ASSIGNMENTS: list[str] = [
    "RM-API-IBU", "RM-EXC-MCC", "RM-EXC-CCS", "RM-EXC-PVP", "RM-EXC-MGST",
    "RM-COAT-OPW", "RM-WATER-PW",
    "SF-GRANULE", "SF-TABLET-UC",
    "PKG-BLISTER", "PKG-LIDDING", "PKG-CARTON", "PKG-INSERT", "PKG-SEAL",
]

# ---------------------------------------------------------------------------
# Storage Locations  (inventory module)
# ---------------------------------------------------------------------------

STORAGE_LOCATIONS: list[dict] = [
    # Receiving
    {"code": "PHX-RECV-01",    "name": "Pharma Receiving Dock",          "location_type": "receiving", "description": "Inbound goods receipt and quarantine staging"},
    # Controlled substance vault
    {"code": "PHX-API-VAULT",  "name": "API / Controlled Substance Vault","location_type": "storage",  "aisle": "V", "bay": "01", "tier": "01", "description": "High-security cGMP vault for API and Schedule substances"},
    # Excipient warehouse
    {"code": "PHX-WH-EXCIP",   "name": "Excipient Warehouse",            "location_type": "storage",  "aisle": "A", "bay": "01", "tier": "01", "description": "MCC, CCS, PVP, Mg stearate, Opadry"},
    # Packaging materials warehouse
    {"code": "PHX-WH-PKG",     "name": "Packaging Materials Warehouse",  "location_type": "storage",  "aisle": "B", "bay": "01", "tier": "01", "description": "Blister film, lidding, cartons, inserts, seals"},
    # WFI / purified water holding
    {"code": "PHX-WH-WATER",   "name": "Purified Water Holding",         "location_type": "storage",  "aisle": "A", "bay": "02", "tier": "01", "description": "On-site WFI / purified water storage tank"},
    # Staging area
    {"code": "PHX-STG-01",     "name": "Dispensing Staging Area",        "location_type": "staging",  "description": "Pre-dispensing material staging (verified identity/quantity)"},
    # Raw-and-in-process (line-side)
    {"code": "PHX-RIP-GRAN",   "name": "RIP — Granulation",              "location_type": "rip",      "description": "Line-side raw materials for granulation step (seq 10/20)"},
    {"code": "PHX-RIP-PRESS",  "name": "RIP — Compression",              "location_type": "rip",      "description": "Line-side granule blend for compression step (seq 60)"},
    {"code": "PHX-RIP-COAT",   "name": "RIP — Film Coating",             "location_type": "rip",      "description": "Line-side tablet cores + Opadry for coating step (seq 80)"},
    {"code": "PHX-RIP-PACK",   "name": "RIP — Packaging",                "location_type": "rip",      "description": "Line-side tablets + packaging materials for step (seq 100)"},
    # QC sample hold
    {"code": "PHX-QC-HOLD",    "name": "QC Sample Hold",                 "location_type": "storage",  "aisle": "C", "bay": "01", "tier": "01", "description": "Retain samples pending release-test results"},
    # Finished-goods quarantine (batch held until QC release)
    {"code": "PHX-FG-QUAR",    "name": "Finished Goods Quarantine",      "location_type": "storage",  "aisle": "D", "bay": "01", "tier": "01", "description": "Packaged batch quarantine pending batch-record review"},
    # Shipping dock
    {"code": "PHX-SHIP-01",    "name": "Shipping Dock",                  "location_type": "shipping", "description": "Outbound finished goods dispatch"},
]

# Map material code → warehouse storage location after receiving
MATERIAL_STORAGE_MAP: dict[str, str] = {
    "RM-API-IBU":   "PHX-API-VAULT",
    "RM-EXC-MCC":   "PHX-WH-EXCIP",
    "RM-EXC-CCS":   "PHX-WH-EXCIP",
    "RM-EXC-PVP":   "PHX-WH-EXCIP",
    "RM-EXC-MGST":  "PHX-WH-EXCIP",
    "RM-COAT-OPW":  "PHX-WH-EXCIP",
    "RM-WATER-PW":  "PHX-WH-WATER",
    "PKG-BLISTER":  "PHX-WH-PKG",
    "PKG-LIDDING":  "PHX-WH-PKG",
    "PKG-CARTON":   "PHX-WH-PKG",
    "PKG-INSERT":   "PHX-WH-PKG",
    "PKG-SEAL":     "PHX-WH-PKG",
}

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Equipment Capabilities (declared capability per instance)
# ---------------------------------------------------------------------------

EQUIPMENT_CAPABILITIES: list[dict] = [
    {"equipment_code": "DISP-001",   "equipment_class_code": "DISPENSING_BOOTH", "capability_type": "available", "reason": "Calibrated; environmental monitoring current",
     "properties": [{"property_name": "max_batch_size_kg", "value": "200"}, {"property_name": "balance_readability_g", "value": "0.1"}]},
    {"equipment_code": "HSG-001",    "equipment_class_code": "GRANULATOR",       "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "bowl_volume_l", "value": "150"}, {"property_name": "max_impeller_rpm", "value": "500"}]},
    {"equipment_code": "FBD-001",    "equipment_class_code": "FLUID_BED_DRYER",  "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_inlet_temp_c", "value": "90"}, {"property_name": "bowl_volume_l", "value": "300"}]},
    {"equipment_code": "MILL-001",   "equipment_class_code": "SIZE_MILL",        "capability_type": "available", "reason": "Nominal"},
    {"equipment_code": "BLEND-001",  "equipment_class_code": "BIN_BLENDER",      "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "bin_volume_l", "value": "500"}]},
    {"equipment_code": "BLEND-002",  "equipment_class_code": "BIN_BLENDER",      "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "bin_volume_l", "value": "500"}]},
    {"equipment_code": "PRESS-001",  "equipment_class_code": "TABLET_PRESS",     "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_compression_n", "value": "40000"}, {"property_name": "max_turret_rpm", "value": "60"}, {"property_name": "punch_count", "value": "36"}]},
    {"equipment_code": "PRESS-002",  "equipment_class_code": "TABLET_PRESS",     "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_compression_n", "value": "40000"}, {"property_name": "max_turret_rpm", "value": "60"}, {"property_name": "punch_count", "value": "36"}]},
    {"equipment_code": "COATER-001", "equipment_class_code": "FILM_COATER",      "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "pan_volume_l", "value": "60"}, {"property_name": "max_load_kg", "value": "40"}]},
    {"equipment_code": "QCLAB-001",  "equipment_class_code": "PHARMA_ANALYZER",  "capability_type": "available", "reason": "Calibrated; HPLC, dissolution, hardness tester current"},
    {"equipment_code": "BPAK-001",   "equipment_class_code": "BLISTER_PACKER",   "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_strokes_per_min", "value": "60"}, {"property_name": "max_blister_width_mm", "value": "130"}]},
    {"equipment_code": "REWORK-001", "equipment_class_code": "MRB_STATION",      "capability_type": "available", "reason": "MRB / rework bench"},
]
