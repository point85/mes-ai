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
# Dispositions (top-level entities)
# ---------------------------------------------------------------------------

DISPOSITIONS: list[dict] = [
    # Per-edge dispositions for the route graph. Each entry below appears
    # in exactly one step's output list AND at most one step's input list,
    # which keeps every (output → input) edge unambiguous.
    {"code": "BLEND-DONE",   "name": "Blend Complete",         "description": "Blending finished, advance to pasteurization", "category": "route"},
    {"code": "PAST-DONE",    "name": "Pasteurization Complete","description": "Pasteurization finished, advance to QC",        "category": "route"},
    {"code": "QC-PASS",      "name": "QC Pass",                "description": "Quality test passed",                          "category": "route"},
    {"code": "QC-FAIL",      "name": "QC Fail",                "description": "Quality test failed — send to rework",         "category": "route"},
    {"code": "ESC-MRB",      "name": "Escalate to MRB",        "description": "Escalate to Material Review Board",            "category": "hold"},
    {"code": "REWORK-DONE",  "name": "Rework Complete",        "description": "Re-blend complete, return to pasteurization", "category": "route"},
    {"code": "FILL-DONE",    "name": "Fill Complete",          "description": "Filling/capping done, advance to packing",     "category": "route"},
    {"code": "RETURN-BLEND", "name": "Return to Blend",        "description": "MRB decision: send back to blending",          "category": "hold"},
    {"code": "USE-AS-IS",    "name": "Use As-Is",              "description": "MRB decision: bypass rework, advance to fill", "category": "hold"},
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
        "is_initial_step": True,
        "input_disposition_codes": [],              # entry point — no incoming edges
        "output_disposition_codes": ["BLEND-DONE"],
    },
    {
        "sequence": 20,
        "name": "Pasteurization",
        "step_type": "production",
        "work_cell_code": "WC-PAST",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0020",
        "input_disposition_codes": ["BLEND-DONE", "REWORK-DONE"],
        "output_disposition_codes": ["PAST-DONE"],
    },
    {
        "sequence": 30,
        "name": "Quality Testing",
        "step_type": "inspection",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 300.0,
        "erp_operation_number": "0030",
        "input_disposition_codes": ["PAST-DONE"],
        "output_disposition_codes": ["QC-PASS", "QC-FAIL", "ESC-MRB"],
    },
    {
        "sequence": 40,
        "name": "Filling & Capping",
        "step_type": "production",
        "work_cell_code": "WC-FILL",
        "expected_cycle_time_sec": 1200.0,
        "erp_operation_number": "0040",
        "input_disposition_codes": ["QC-PASS", "USE-AS-IS"],
        "output_disposition_codes": ["FILL-DONE"],
    },
    {
        "sequence": 50,
        "name": "Labeling & Packing",
        "step_type": "production",
        "work_cell_code": "WC-PACK",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0050",
        "input_disposition_codes": ["FILL-DONE"],
        "output_disposition_codes": [],  # terminal
    },
    {
        "sequence": 60,
        "name": "Re‑Blend (Rework)",
        "step_type": "rework",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0060",
        "input_disposition_codes": ["QC-FAIL", "RETURN-BLEND"],
        "output_disposition_codes": ["REWORK-DONE"],
    },
    {
        "sequence": 70,
        "name": "MRB Review",
        "step_type": "mrb",
        "work_cell_code": "WC-QC",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0070",
        "input_disposition_codes": ["ESC-MRB"],
        "output_disposition_codes": ["RETURN-BLEND", "USE-AS-IS"],
    },
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

# Data definitions kept here are those with NO matching step parameter (unique time-series
# measurements). Parameters that duplicate step parameters were removed — use step parameters
# for spec-limit display; use data definitions for time-series data collection only.
DATA_DEFS: dict[int, list[dict]] = {
    10: [  # Blending — three unique measurements not covered by step parameters
        {"code": "CPG-BLEND-TIME",  "name": "Blend Mix Time",    "data_type": "numeric", "source": "equipment", "lower_limit": 12.0, "upper_limit": 20.0, "uom": "min", "is_required": True},
        {"code": "CPG-BLEND-TEMP",  "name": "Blend Temperature", "data_type": "numeric", "source": "sensor",    "lower_limit": 20.0, "upper_limit": 30.0, "uom": "°C",  "is_required": True},
        {"code": "CPG-BLEND-RATIO", "name": "Blend Ratio (W:C)", "data_type": "numeric", "source": "equipment", "lower_limit": 3.8,  "upper_limit": 4.2,  "uom": None,  "is_required": True},
    ],
    30: [  # Quality Testing — Brix Value and pH Value are unique (step params use different names)
        {"code": "CPG-QC-BRIX", "name": "Brix Value", "data_type": "numeric", "source": "manual", "lower_limit": 11.0, "upper_limit": 12.0, "uom": "°Bx", "is_required": True},
        {"code": "CPG-QC-PH",   "name": "pH Value",   "data_type": "numeric", "source": "manual", "lower_limit": 3.5,  "upper_limit": 4.0,  "uom": None,  "is_required": True},
    ],
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
    {"code": "WC-BLEND",  "name": "Blending Station",      "description": "Tank mixer for juice blending"},
    {"code": "WC-PAST",   "name": "Pasteurization Station", "description": "HTST pasteurizer"},
    {"code": "WC-QC",     "name": "QC Lab Station",         "description": "Quality control testing bench"},
    {"code": "WC-FILL",   "name": "Filling Station",        "description": "Bottle filling and capping"},
    {"code": "WC-PACK",   "name": "Packing Station",        "description": "Label application and case packing"},
    {"code": "WC-REWORK", "name": "Rework Station",         "description": "Juice adjustment/rework tank"},
]

EQUIPMENT: list[dict] = [
    {"code": "TM-100",   "name": "Tank Mixer TM-100",     "work_cell_code": "WC-BLEND",  "state_model": "semi_e10",  "max_queue_depth": 2},
    {"code": "PS-200",   "name": "HTST Pasteurizer PS-200","work_cell_code": "WC-PAST",   "state_model": "packml",    "max_queue_depth": 1},
    {"code": "QC-300",   "name": "Lab Analyzer QC-300",    "work_cell_code": "WC-QC",     "state_model": "semi_e10",  "max_queue_depth": 3},
    {"code": "FL-400A",  "name": "Filler FL-400A",         "work_cell_code": "WC-FILL",   "state_model": "packml",    "max_queue_depth": 2},
    {"code": "FL-400B",  "name": "Filler FL-400B",         "work_cell_code": "WC-FILL",   "state_model": "packml",    "max_queue_depth": 2},
    {"code": "LP-500",   "name": "Labeler/Packer LP-500",  "work_cell_code": "WC-PACK",   "state_model": "packml",    "max_queue_depth": 2},
    {"code": "RW-600",   "name": "Adjustment Tank RW-600", "work_cell_code": "WC-REWORK", "state_model": "semi_e10",  "max_queue_depth": 2},
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
# ISA-95 Part 2: Equipment Classes & Properties
# ---------------------------------------------------------------------------

EQUIPMENT_CLASSES: list[dict] = [
    {"code": "MIXER",       "name": "Mixer",           "description": "Blending / mixing equipment"},
    {"code": "PASTEURIZER", "name": "Pasteurizer",     "description": "Heat-treatment equipment (HTST, UHT)"},
    {"code": "ANALYZER",    "name": "Analyzer",        "description": "Quality-control analytical instrument"},
    {"code": "FILLER",      "name": "Filler",          "description": "Liquid filling and capping equipment"},
    {"code": "LABELER",     "name": "Labeler / Packer","description": "Label application and case packing"},
    {"code": "TANK",        "name": "Tank",            "description": "Holding / rework tank"},
]

EQUIPMENT_CLASS_PROPERTIES: list[dict] = [
    # Mixer
    {"class_code": "MIXER",       "name": "max_volume_l",   "data_type": "float",  "uom_id": "L",           "default_value": "10000", "description": "Max batch volume"},
    {"class_code": "MIXER",       "name": "max_rpm",        "data_type": "float",  "uom_id": "RPM",         "default_value": "1800",  "description": "Maximum impeller speed"},
    # Pasteurizer
    {"class_code": "PASTEURIZER", "name": "max_temp_c",     "data_type": "float",  "uom_id": "°C",          "default_value": "95",    "description": "Max temperature"},
    {"class_code": "PASTEURIZER", "name": "hold_time_s",    "data_type": "float",  "uom_id": "s",           "default_value": "15",    "description": "Minimum hold time"},
    # Filler
    {"class_code": "FILLER",      "name": "max_fill_rate",  "data_type": "float",  "uom_id": "bottle/min",  "default_value": "600",   "description": "Max fill rate"},
    {"class_code": "FILLER",      "name": "min_fill_vol_ml","data_type": "float",  "uom_id": "mL",          "default_value": "100",   "description": "Minimum fill volume"},
    # Labeler
    {"class_code": "LABELER",     "name": "max_label_rate", "data_type": "float",  "uom_id": "label/min",   "default_value": "600",   "description": "Max labels per minute"},
]

# Maps equipment code → equipment class code
EQUIPMENT_CLASS_MAP: dict[str, str] = {
    "TM-100":  "MIXER",
    "PS-200":  "PASTEURIZER",
    "QC-300":  "ANALYZER",
    "FL-400A": "FILLER",
    "FL-400B": "FILLER",
    "LP-500":  "LABELER",
    "RW-600":  "TANK",
}

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

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Process Segment → Equipment Class (dispatch constraint)
# ---------------------------------------------------------------------------
# Each process segment declares what class of equipment it needs; the
# dispatcher uses this to narrow the candidate set before applying
# SegmentEquipmentRequirement preferences below.

STEP_EQUIPMENT_CLASS: dict[int, str] = {
    10: "MIXER",        # Blending
    20: "PASTEURIZER",  # Pasteurization
    30: "ANALYZER",     # Quality Testing
    40: "FILLER",       # Filling & Capping
    50: "LABELER",      # Labeling & Packing
    60: "TANK",         # Re-Blend (Rework)
    70: "ANALYZER",     # MRB Review (lab bench)
}

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Segment Equipment Requirements
# ---------------------------------------------------------------------------
# Specific-equipment preferences that augment the class-level constraint above.
# use_type: "required" | "preferred" | "alternate"

SEGMENT_EQUIPMENT_REQUIREMENTS: list[dict] = [
    # Blending — only one mixer
    {"step_sequence": 10, "equipment_code": "TM-100",  "use_type": "required",  "description": "Primary blending mixer"},
    # Pasteurization — only one pasteurizer
    {"step_sequence": 20, "equipment_code": "PS-200",  "use_type": "required",  "description": "HTST pasteurizer"},
    # QC — analytical bench
    {"step_sequence": 30, "equipment_code": "QC-300",  "use_type": "required",  "description": "Lab analyzer"},
    # Filling — dual fillers for load balancing
    {"step_sequence": 40, "equipment_code": "FL-400A", "use_type": "preferred", "description": "Primary filler"},
    {"step_sequence": 40, "equipment_code": "FL-400B", "use_type": "alternate", "description": "Secondary filler (load balancing)"},
    # Labeling / Packing
    {"step_sequence": 50, "equipment_code": "LP-500",  "use_type": "required",  "description": "Labeler / case packer"},
    # Rework
    {"step_sequence": 60, "equipment_code": "RW-600",  "use_type": "required",  "description": "Adjustment / rework tank"},
    # MRB — reuses the QC analyzer
    {"step_sequence": 70, "equipment_code": "QC-300",  "use_type": "preferred", "description": "MRB review at QC bench"},
]

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Segment Material Requirements
# ---------------------------------------------------------------------------
# Declarative per-segment consumed/produced materials.  Complements the
# product-specific BillOfMaterial (BOMItem) by describing the segment's
# material behavior independent of any particular product.

SEGMENT_MATERIAL_REQUIREMENTS: list[dict] = [
    # 10 — Blending: consume raws, produce blended juice
    {"step_sequence": 10, "material_code": "RM-OJ-CONC",    "quantity": 200.0,  "uom": "kg", "material_use": "consumed", "position": 10, "description": "Orange juice concentrate"},
    {"step_sequence": 10, "material_code": "RM-WATER",      "quantity": 800.0,  "uom": "L",  "material_use": "consumed", "position": 20, "description": "Purified water"},
    {"step_sequence": 10, "material_code": "RM-SUGAR",      "quantity": 50.0,   "uom": "kg", "material_use": "consumed", "position": 30, "description": "Cane sugar"},
    {"step_sequence": 10, "material_code": "RM-CITRIC",     "quantity": 2.0,    "uom": "kg", "material_use": "consumed", "position": 40, "description": "Citric acid"},
    {"step_sequence": 10, "material_code": "RM-VITC",       "quantity": 0.5,    "uom": "kg", "material_use": "consumed", "position": 50, "description": "Vitamin C powder"},
    {"step_sequence": 10, "material_code": "SF-JUICE-BLEND","quantity": 1000.0, "uom": "L",  "material_use": "produced", "position": 60, "description": "Blended juice (batch output)"},
    # 20 — Pasteurization: heat-treated but same material; no consume/produce needed
    # 40 — Filling & Capping
    {"step_sequence": 40, "material_code": "SF-JUICE-BLEND","quantity": 1000.0, "uom": "L",  "material_use": "consumed", "position": 10, "description": "Blended juice input"},
    {"step_sequence": 40, "material_code": "PKG-BOTTLE-1L", "quantity": 1000.0, "uom": "EA", "material_use": "consumed", "position": 20, "description": "1 L PET bottles"},
    {"step_sequence": 40, "material_code": "PKG-CAP",       "quantity": 1000.0, "uom": "EA", "material_use": "consumed", "position": 30, "description": "Bottle caps"},
    # 50 — Labeling & Packing: produces the finished good
    {"step_sequence": 50, "material_code": "PKG-LABEL",     "quantity": 1000.0, "uom": "EA", "material_use": "consumed", "position": 10, "description": "Product labels"},
    {"step_sequence": 50, "material_code": "PKG-CASE",      "quantity": 84.0,   "uom": "EA", "material_use": "consumed", "position": 20, "description": "Shipping cases (12-pack)"},
    {"step_sequence": 50, "material_code": "FG-OJ-1L",      "quantity": 1000.0, "uom": "EA", "material_use": "produced", "position": 30, "description": "Finished Premium Orange Juice 1 L"},
]

# ---------------------------------------------------------------------------
# OperationsDefinition ↔ Material assignments (route-level raw materials)
# ---------------------------------------------------------------------------
# Declares every material referenced anywhere in the bottling route.  Lets
# the ERP/MES see the full raw-material list for a route at a glance.

ROUTE_MATERIAL_ASSIGNMENTS: list[str] = [
    "RM-OJ-CONC", "RM-WATER", "RM-SUGAR", "RM-CITRIC", "RM-VITC",
    "SF-JUICE-BLEND",
    "PKG-BOTTLE-1L", "PKG-CAP", "PKG-LABEL", "PKG-CASE",
    "FG-OJ-1L",
]

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Equipment Capabilities (declared capability of each instance)
# ---------------------------------------------------------------------------
# Each capability entry is:
#   equipment_code           → equipment instance
#   equipment_class_code     → what class of work this declares capability for
#   capability_type          → available | committed | unattainable
#   reason                   → free-text status line
#   properties (optional)    → list of {"property_name", "value"} pairs.
#                              property_name must match an EquipmentClassProperty
#                              name defined above; seed code looks up the
#                              class_property_id at insert time.

EQUIPMENT_CAPABILITIES: list[dict] = [
    {"equipment_code": "TM-100",  "equipment_class_code": "MIXER",       "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_volume_l", "value": "1500"}, {"property_name": "max_rpm", "value": "250"}]},
    {"equipment_code": "PS-200",  "equipment_class_code": "PASTEURIZER", "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_temp_c", "value": "85"}, {"property_name": "hold_time_s", "value": "15"}]},
    {"equipment_code": "QC-300",  "equipment_class_code": "ANALYZER",    "capability_type": "available", "reason": "Nominal"},
    {"equipment_code": "FL-400A", "equipment_class_code": "FILLER",      "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_fill_rate", "value": "300"}, {"property_name": "min_fill_vol_ml", "value": "200"}]},
    {"equipment_code": "FL-400B", "equipment_class_code": "FILLER",      "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_fill_rate", "value": "300"}, {"property_name": "min_fill_vol_ml", "value": "200"}]},
    {"equipment_code": "LP-500",  "equipment_class_code": "LABELER",     "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_label_rate", "value": "350"}]},
    {"equipment_code": "RW-600",  "equipment_class_code": "TANK",        "capability_type": "available", "reason": "Adjustment tank"},
]
