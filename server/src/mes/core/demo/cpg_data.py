"""
CPG Demo: Juice Bottling Line data constants.

Defines all materials, product, BOM, route steps, transitions,
step parameters, data definitions, quality tests, production orders,
and the ISA‑95 physical hierarchy for a single‑product orange‑juice
bottling demonstration scenario.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MATERIALS: list[dict] = [
    {"code": "RM-OJ-CONC",     "name": "Orange Juice Concentrate", "material_type": "raw",           "uom": "kg"},
    {"code": "RM-WATER",       "name": "Purified Water",           "material_type": "raw",           "uom": "L"},
    {"code": "RM-SUGAR",       "name": "Cane Sugar",               "material_type": "raw",           "uom": "kg"},
    {"code": "RM-CITRIC",      "name": "Citric Acid",              "material_type": "raw",           "uom": "kg"},
    {"code": "RM-VITC",        "name": "Vitamin C Powder",         "material_type": "raw",           "uom": "kg"},
    {"code": "SF-JUICE-BLEND", "name": "Blended Juice",            "material_type": "semi_finished", "uom": "L"},
    {"code": "PKG-BOTTLE-1L",  "name": "PET Bottle 1 L",          "material_type": "packaging",     "uom": "EA"},
    {"code": "PKG-CAP",        "name": "Bottle Cap",               "material_type": "packaging",     "uom": "EA"},
    {"code": "PKG-LABEL",      "name": "Product Label",            "material_type": "packaging",     "uom": "EA"},
    {"code": "PKG-CASE",       "name": "Shipping Case (12‑pack)",  "material_type": "packaging",     "uom": "EA"},
    {"code": "FG-OJ-1L",      "name": "Premium Orange Juice 1 L", "material_type": "finished",      "uom": "EA"},
]

# ---------------------------------------------------------------------------
# Material Lots  (initial inventory for demo)
# ---------------------------------------------------------------------------

MATERIAL_LOTS: list[dict] = [
    {"material_code": "RM-OJ-CONC",    "lot_number": "OJC-2026-001",   "quantity_on_hand": 5000.0,   "supplier": "Florida Citrus Co."},
    {"material_code": "RM-WATER",      "lot_number": "H2O-2026-001",   "quantity_on_hand": 20000.0,  "supplier": "AquaPure Inc."},
    {"material_code": "RM-SUGAR",      "lot_number": "SUG-2026-001",   "quantity_on_hand": 2000.0,   "supplier": "CaneSweet Ltd."},
    {"material_code": "RM-CITRIC",     "lot_number": "CIT-2026-001",   "quantity_on_hand": 100.0,    "supplier": "ChemSupply Co."},
    {"material_code": "RM-VITC",       "lot_number": "VTC-2026-001",   "quantity_on_hand": 25.0,     "supplier": "NutriChem Inc."},
    {"material_code": "PKG-BOTTLE-1L", "lot_number": "BTL-2026-001",   "quantity_on_hand": 50000.0,  "supplier": "PETpack Corp."},
    {"material_code": "PKG-CAP",       "lot_number": "CAP-2026-001",   "quantity_on_hand": 50000.0,  "supplier": "PETpack Corp."},
    {"material_code": "PKG-LABEL",     "lot_number": "LBL-2026-001",   "quantity_on_hand": 50000.0,  "supplier": "PrintWorks Ltd."},
    {"material_code": "PKG-CASE",      "lot_number": "CSE-2026-001",   "quantity_on_hand": 5000.0,   "supplier": "BoxCo Packaging"},
]

# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

PRODUCT = {
    "code": "FG-OJ-1L",
    "name": "Premium Orange Juice 1 L",
    "version": "1.0",
    "product_type": "process",
    "description": "1‑litre PET bottle of premium orange juice",
    "uom": "EA",
}

# ---------------------------------------------------------------------------
# Bill of Material  (per lot = 1 000 bottles)
# ---------------------------------------------------------------------------

BOM_ITEMS: list[dict] = [
    {"material_code": "RM-OJ-CONC",    "quantity": 200.0,   "uom": "kg", "position": 10, "step_sequence": 10},   # Blending
    {"material_code": "RM-WATER",      "quantity": 800.0,   "uom": "L",  "position": 20, "step_sequence": 10},   # Blending
    {"material_code": "RM-SUGAR",      "quantity": 50.0,    "uom": "kg", "position": 30, "step_sequence": 10},   # Blending
    {"material_code": "RM-CITRIC",     "quantity": 2.0,     "uom": "kg", "position": 40, "step_sequence": 10},   # Blending
    {"material_code": "RM-VITC",       "quantity": 0.5,     "uom": "kg", "position": 50, "step_sequence": 10},   # Blending
    {"material_code": "PKG-BOTTLE-1L", "quantity": 1000.0,  "uom": "EA", "position": 60, "step_sequence": 40},   # Filling & Capping
    {"material_code": "PKG-CAP",       "quantity": 1000.0,  "uom": "EA", "position": 70, "step_sequence": 40},   # Filling & Capping
    {"material_code": "PKG-LABEL",     "quantity": 1000.0,  "uom": "EA", "position": 80, "step_sequence": 50},   # Labeling & Packing
    {"material_code": "PKG-CASE",      "quantity": 84.0,    "uom": "EA", "position": 90, "step_sequence": 50},   # Labeling & Packing
]

# ---------------------------------------------------------------------------
# Route Steps
# ---------------------------------------------------------------------------

ROUTE_NAME = "Juice Bottling Line"

STEPS: list[dict] = [
    {
        "sequence": 10,
        "name": "Blending",
        "step_type": "production",
        "work_cell_code": "WC-BLEND",
        "expected_cycle_time_sec": 900.0,
        "erp_operation_number": "0010",
    },
    {
        "sequence": 20,
        "name": "Pasteurization",
        "step_type": "production",
        "work_cell_code": "WC-PAST",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0020",
    },
    {
        "sequence": 30,
        "name": "Quality Testing",
        "step_type": "inspection",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 300.0,
        "erp_operation_number": "0030",
    },
    {
        "sequence": 40,
        "name": "Filling & Capping",
        "step_type": "production",
        "work_cell_code": "WC-FILL",
        "expected_cycle_time_sec": 1200.0,
        "erp_operation_number": "0040",
    },
    {
        "sequence": 50,
        "name": "Labeling & Packing",
        "step_type": "production",
        "work_cell_code": "WC-PACK",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0050",
    },
    {
        "sequence": 60,
        "name": "Re‑Blend (Rework)",
        "step_type": "rework",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0060",
    },
    {
        "sequence": 70,
        "name": "MRB Review",
        "step_type": "mrb",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0070",
    },
]

# ---------------------------------------------------------------------------
# Step Transitions  (graph routing)
#
# Keyed by (from_sequence, to_sequence) with condition metadata.
# ---------------------------------------------------------------------------

TRANSITIONS: list[dict] = [
    # Blend → Pasteurize (always)
    {"from_seq": 10, "to_seq": 20, "condition": "always",      "priority": 0, "is_default": True,  "label": None},
    # Pasteurize → QC (always)
    {"from_seq": 20, "to_seq": 30, "condition": "always",      "priority": 0, "is_default": True,  "label": None},
    # QC → Fill (on_pass)
    {"from_seq": 30, "to_seq": 40, "condition": "on_pass",     "priority": 10, "is_default": True,  "label": "QC Passed"},
    # QC → Re-Blend (on_fail)
    {"from_seq": 30, "to_seq": 60, "condition": "on_fail",     "priority": 10, "is_default": False, "label": "QC Failed — Re-Blend"},
    # QC → MRB (disposition)
    {"from_seq": 30, "to_seq": 70, "condition": "disposition",  "priority": 20, "is_default": False, "label": "Send to MRB"},
    # Fill → Pack (always)
    {"from_seq": 40, "to_seq": 50, "condition": "always",      "priority": 0, "is_default": True,  "label": None},
    # Re-Blend → Pasteurize (rework loop back)
    {"from_seq": 60, "to_seq": 20, "condition": "always",      "priority": 0, "is_default": True,  "label": "Return to Pasteurization"},
    # MRB → Blend (disposition: return)
    {"from_seq": 70, "to_seq": 10, "condition": "disposition",  "priority": 10, "is_default": False, "label": "Return to Blend"},
    # MRB → Fill (disposition: use-as-is)
    {"from_seq": 70, "to_seq": 40, "condition": "disposition",  "priority": 10, "is_default": False, "label": "Use As‑Is"},
]

# ---------------------------------------------------------------------------
# Step Parameters  (recipe / spec targets)
# ---------------------------------------------------------------------------

STEP_PARAMS: dict[int, list[dict]] = {
    10: [  # Blending
        {"name": "Mix Time",        "data_type": "numeric", "target_value": "15",  "lower_limit": "12",   "upper_limit": "20",   "uom": "min", "is_required": True},
        {"name": "Mix Temperature", "data_type": "numeric", "target_value": "25",  "lower_limit": "20",   "upper_limit": "30",   "uom": "°C",  "is_required": True},
        {"name": "Blend Ratio",     "data_type": "numeric", "target_value": "4.0", "lower_limit": "3.8",  "upper_limit": "4.2",  "uom": None,  "is_required": True},
    ],
    20: [  # Pasteurization
        {"name": "HTST Temperature", "data_type": "numeric", "target_value": "72.0", "lower_limit": "71.5", "upper_limit": "73.0", "uom": "°C", "is_required": True},
        {"name": "Hold Time",        "data_type": "numeric", "target_value": "15",   "lower_limit": "15",   "upper_limit": "20",   "uom": "s",  "is_required": True},
        {"name": "Exit Temperature", "data_type": "numeric", "target_value": "4.0",  "lower_limit": "2.0",  "upper_limit": "6.0",  "uom": "°C", "is_required": True},
    ],
    30: [  # QC Testing
        {"name": "Brix",           "data_type": "numeric", "target_value": "11.5", "lower_limit": "11.0", "upper_limit": "12.0", "uom": "°Bx",    "is_required": True},
        {"name": "pH",             "data_type": "numeric", "target_value": "3.8",  "lower_limit": "3.5",  "upper_limit": "4.0",  "uom": None,     "is_required": True},
        {"name": "Microbial Count","data_type": "numeric", "target_value": "0",    "lower_limit": "0",    "upper_limit": "10",   "uom": "CFU/mL", "is_required": True},
        {"name": "Color Index",    "data_type": "numeric", "target_value": "35",   "lower_limit": "30",   "upper_limit": "40",   "uom": None,     "is_required": True},
        {"name": "Taste Approved", "data_type": "boolean", "target_value": "true", "lower_limit": None,   "upper_limit": None,   "uom": None,     "is_required": True},
    ],
    40: [  # Filling & Capping
        {"name": "Fill Volume", "data_type": "numeric", "target_value": "1000", "lower_limit": "995",  "upper_limit": "1010", "uom": "mL", "is_required": True},
        {"name": "Cap Torque",  "data_type": "numeric", "target_value": "1.2",  "lower_limit": "1.0",  "upper_limit": "1.5",  "uom": "Nm", "is_required": True},
        {"name": "Headspace",   "data_type": "numeric", "target_value": "15",   "lower_limit": "10",   "upper_limit": "20",   "uom": "mm", "is_required": True},
    ],
    50: [  # Labeling & Packing
        {"name": "Label Aligned",   "data_type": "boolean", "target_value": "true", "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"name": "Date Code Legible","data_type": "boolean", "target_value": "true", "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"name": "Case Count",      "data_type": "numeric", "target_value": "12",   "lower_limit": "12", "upper_limit": "12",  "uom": "EA", "is_required": True},
    ],
    60: [  # Re-Blend
        {"name": "Adjustment Notes",  "data_type": "string", "target_value": None, "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"name": "Corrective Action", "data_type": "enum",   "target_value": None, "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
    ],
    70: [  # MRB Review
        {"name": "Disposition",   "data_type": "enum",   "target_value": None, "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
        {"name": "Review Notes",  "data_type": "string", "target_value": None, "lower_limit": None, "upper_limit": None, "uom": None, "is_required": True},
    ],
}

# ---------------------------------------------------------------------------
# Data Collection Definitions  (actual measurement collection)
# ---------------------------------------------------------------------------

DATA_DEFS: dict[int, list[dict]] = {
    10: [
        {"code": "CPG-BLEND-TIME",  "name": "Blend Mix Time",        "data_type": "numeric", "source": "equipment", "lower_limit": 12.0,  "upper_limit": 20.0,  "uom": "min", "is_required": True},
        {"code": "CPG-BLEND-TEMP",  "name": "Blend Temperature",     "data_type": "numeric", "source": "sensor",    "lower_limit": 20.0,  "upper_limit": 30.0,  "uom": "°C",  "is_required": True},
        {"code": "CPG-BLEND-RATIO", "name": "Blend Ratio (W:C)",     "data_type": "numeric", "source": "equipment", "lower_limit": 3.8,   "upper_limit": 4.2,   "uom": None,  "is_required": True},
    ],
    20: [
        {"code": "CPG-PAST-TEMP",   "name": "HTST Temperature",      "data_type": "numeric", "source": "equipment", "lower_limit": 71.5,  "upper_limit": 73.0,  "uom": "°C", "is_required": True},
        {"code": "CPG-PAST-HOLD",   "name": "Hold Time",             "data_type": "numeric", "source": "equipment", "lower_limit": 15.0,  "upper_limit": 20.0,  "uom": "s",  "is_required": True},
        {"code": "CPG-PAST-EXIT",   "name": "Exit Temperature",      "data_type": "numeric", "source": "sensor",    "lower_limit": 2.0,   "upper_limit": 6.0,   "uom": "°C", "is_required": True},
    ],
    30: [
        {"code": "CPG-QC-BRIX",     "name": "Brix Value",            "data_type": "numeric", "source": "manual",    "lower_limit": 11.0,  "upper_limit": 12.0,  "uom": "°Bx",    "is_required": True},
        {"code": "CPG-QC-PH",       "name": "pH Value",              "data_type": "numeric", "source": "manual",    "lower_limit": 3.5,   "upper_limit": 4.0,   "uom": None,     "is_required": True},
        {"code": "CPG-QC-MICRO",    "name": "Microbial Count",       "data_type": "numeric", "source": "manual",    "lower_limit": 0.0,   "upper_limit": 10.0,  "uom": "CFU/mL", "is_required": True},
        {"code": "CPG-QC-COLOR",    "name": "Color Index",           "data_type": "numeric", "source": "manual",    "lower_limit": 30.0,  "upper_limit": 40.0,  "uom": None,     "is_required": True},
        {"code": "CPG-QC-TASTE",    "name": "Taste Approved",        "data_type": "boolean", "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None,     "is_required": True},
    ],
    40: [
        {"code": "CPG-FILL-VOL",    "name": "Fill Volume",           "data_type": "numeric", "source": "equipment", "lower_limit": 995.0, "upper_limit": 1010.0,"uom": "mL", "is_required": True},
        {"code": "CPG-FILL-TORQUE", "name": "Cap Torque",            "data_type": "numeric", "source": "equipment", "lower_limit": 1.0,   "upper_limit": 1.5,   "uom": "Nm", "is_required": True},
        {"code": "CPG-FILL-HEAD",   "name": "Headspace",             "data_type": "numeric", "source": "sensor",    "lower_limit": 10.0,  "upper_limit": 20.0,  "uom": "mm", "is_required": True},
    ],
    50: [
        {"code": "CPG-PACK-LABEL",  "name": "Label Aligned",         "data_type": "boolean", "source": "sensor",    "lower_limit": None,  "upper_limit": None,  "uom": None, "is_required": True},
        {"code": "CPG-PACK-DATE",   "name": "Date Code Legible",     "data_type": "boolean", "source": "sensor",    "lower_limit": None,  "upper_limit": None,  "uom": None, "is_required": True},
        {"code": "CPG-PACK-COUNT",  "name": "Case Count",            "data_type": "numeric", "source": "equipment", "lower_limit": 12.0,  "upper_limit": 12.0,  "uom": "EA", "is_required": True},
    ],
    60: [
        {"code": "CPG-RW-NOTES",    "name": "Adjustment Notes",      "data_type": "string",  "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None, "is_required": True},
        {"code": "CPG-RW-ACTION",   "name": "Corrective Action",     "data_type": "enum",    "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None, "is_required": True,
         "enum_values": "add_concentrate,add_sugar,add_citric,dilute,other"},
    ],
    70: [
        {"code": "CPG-MRB-DISP",    "name": "Disposition",           "data_type": "enum",    "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None, "is_required": True,
         "enum_values": "return_to_blend,use_as_is,scrap"},
        {"code": "CPG-MRB-NOTES",   "name": "Review Notes",          "data_type": "string",  "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None, "is_required": True},
    ],
}

# ---------------------------------------------------------------------------
# Quality Test  (at QC step 30)
# ---------------------------------------------------------------------------

QUALITY_TEST = {
    "code": "CPG-QC-INLINE",
    "name": "Juice Quality Panel",
    "test_type": "inline",
    "parameters": {
        "description": "Brix, pH, microbial count, color index, and taste panel",
        "pass_criteria": "All numeric parameters within limits and taste approved",
    },
}

# ---------------------------------------------------------------------------
# Production Orders  (removed — create via Production Orders page in ERP Sim)
# ---------------------------------------------------------------------------

ORDERS: list[dict] = []

# ---------------------------------------------------------------------------
# Physical Model  (ISA‑95 hierarchy)
# ---------------------------------------------------------------------------

SITE = {"code": "SB-PLANT", "name": "Sunrise Beverages", "description": "Juice production facility", "timezone": "America/New_York"}
AREA = {"code": "SB-JUICE", "name": "Juice Processing", "description": "Juice blending, pasteurization, and bottling"}
LINE = {"code": "SB-LINE-01", "name": "Bottling Line 1", "description": "Single-product juice bottling line"}

WORK_CELLS: list[dict] = [
    {"code": "WC-BLEND",  "name": "Blending Station",      "wc_type": "automated", "description": "Tank mixer for juice blending"},
    {"code": "WC-PAST",   "name": "Pasteurization Station", "wc_type": "automated", "description": "HTST pasteurizer"},
    {"code": "WC-QC",     "name": "QC Lab Station",         "wc_type": "manual",    "description": "Quality control testing bench"},
    {"code": "WC-FILL",   "name": "Filling Station",        "wc_type": "automated", "description": "Bottle filling and capping"},
    {"code": "WC-PACK",   "name": "Packing Station",        "wc_type": "automated", "description": "Label application and case packing"},
    {"code": "WC-REWORK", "name": "Rework Station",         "wc_type": "manual",    "description": "Juice adjustment/rework tank"},
]

EQUIPMENT: list[dict] = [
    {"code": "TM-100",   "name": "Tank Mixer TM-100",     "work_cell_code": "WC-BLEND",  "equipment_type": "mixer",       "state_model": "semi_e10",  "max_queue_depth": 2},
    {"code": "PS-200",   "name": "HTST Pasteurizer PS-200","work_cell_code": "WC-PAST",   "equipment_type": "pasteurizer", "state_model": "packml",    "max_queue_depth": 1},
    {"code": "QC-300",   "name": "Lab Analyzer QC-300",    "work_cell_code": "WC-QC",     "equipment_type": "analyzer",    "state_model": "semi_e10",  "max_queue_depth": 3},
    {"code": "FL-400A",  "name": "Filler FL-400A",         "work_cell_code": "WC-FILL",   "equipment_type": "filler",      "state_model": "packml",    "max_queue_depth": 2},
    {"code": "FL-400B",  "name": "Filler FL-400B",         "work_cell_code": "WC-FILL",   "equipment_type": "filler",      "state_model": "packml",    "max_queue_depth": 2},
    {"code": "LP-500",   "name": "Labeler/Packer LP-500",  "work_cell_code": "WC-PACK",   "equipment_type": "labeler",     "state_model": "packml",    "max_queue_depth": 2},
    {"code": "RW-600",   "name": "Adjustment Tank RW-600", "work_cell_code": "WC-REWORK", "equipment_type": "tank",        "state_model": "semi_e10",  "max_queue_depth": 2},
]

# Equipment–material assignments  (design speed, target OEE)
EQUIPMENT_MATERIALS: list[dict] = [
    {"equipment_code": "TM-100",  "material_code": "FG-OJ-1L", "design_speed": 200.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 90.0},
    {"equipment_code": "PS-200",  "material_code": "FG-OJ-1L", "design_speed": 250.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 95.0},
    {"equipment_code": "QC-300",  "material_code": "FG-OJ-1L", "design_speed": 100.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 85.0},
    {"equipment_code": "FL-400A", "material_code": "FG-OJ-1L", "design_speed": 300.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "FL-400B", "material_code": "FG-OJ-1L", "design_speed": 300.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "LP-500",  "material_code": "FG-OJ-1L", "design_speed": 350.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 93.0},
    {"equipment_code": "RW-600",  "material_code": "FG-OJ-1L", "design_speed": 100.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 80.0},
]

# ---------------------------------------------------------------------------
# Storage Locations  (inventory module)
# ---------------------------------------------------------------------------

STORAGE_LOCATIONS: list[dict] = [
    # Receiving dock
    {"code": "SB-RECV-01", "name": "Receiving Dock 1",         "location_type": "receiving", "description": "Inbound goods receipt area"},
    # Warehouse storage — one per material group (aisle / bay / tier)
    {"code": "SB-WH-A01",  "name": "Raw Liquids A-01-01",     "location_type": "storage",  "aisle": "A", "bay": "01", "tier": "01", "description": "OJ concentrate, water"},
    {"code": "SB-WH-A02",  "name": "Raw Dry Goods A-01-02",   "location_type": "storage",  "aisle": "A", "bay": "01", "tier": "02", "description": "Sugar, citric acid, vitamin C"},
    {"code": "SB-WH-B01",  "name": "Packaging Stock B-01-01",  "location_type": "storage",  "aisle": "B", "bay": "01", "tier": "01", "description": "Bottles, caps, labels, cases"},
    # Staging area (picked material awaiting line delivery)
    {"code": "SB-STG-01",  "name": "Staging Area 1",           "location_type": "staging",  "description": "Pre-production staging"},
    # Raw-and-In-Process locations at the line (one per consumption point)
    {"code": "SB-RIP-BLEND", "name": "RIP — Blending",        "location_type": "rip",      "description": "Line-side for blending step (seq 10)"},
    {"code": "SB-RIP-FILL",  "name": "RIP — Filling",         "location_type": "rip",      "description": "Line-side for filling step (seq 40)"},
    {"code": "SB-RIP-PACK",  "name": "RIP — Packing",         "location_type": "rip",      "description": "Line-side for labeling/packing step (seq 50)"},
    # Finished goods shipping
    {"code": "SB-SHIP-01",  "name": "Shipping Dock 1",         "location_type": "shipping", "description": "Outbound finished goods"},
]

# Map material codes → which warehouse storage location they go into after receiving
MATERIAL_STORAGE_MAP: dict[str, str] = {
    "RM-OJ-CONC":    "SB-WH-A01",
    "RM-WATER":      "SB-WH-A01",
    "RM-SUGAR":      "SB-WH-A02",
    "RM-CITRIC":     "SB-WH-A02",
    "RM-VITC":       "SB-WH-A02",
    "PKG-BOTTLE-1L": "SB-WH-B01",
    "PKG-CAP":       "SB-WH-B01",
    "PKG-LABEL":     "SB-WH-B01",
    "PKG-CASE":      "SB-WH-B01",
}
