"""
Electronics Demo: PCB Assembly Line data constants.

Defines all materials, product, BOM, route steps, transitions,
step parameters, data definitions, quality tests, production orders,
and the ISA-95 physical hierarchy for a single-product electronic
controller board assembly demonstration scenario.

Tracking: individual units by serial number (discrete manufacturing).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MATERIALS: list[dict] = [
    {"code": "RM-PCB-BLANK",  "name": "Bare PCB Board",              "material_type": "raw",           "uom": "EA"},
    {"code": "RM-SMD-KIT",    "name": "SMD Component Kit",           "material_type": "raw",           "uom": "EA"},
    {"code": "RM-THRU-KIT",   "name": "Through-Hole Component Kit",  "material_type": "raw",           "uom": "EA"},
    {"code": "RM-SOLDER-PST", "name": "Solder Paste Cartridge",      "material_type": "raw",           "uom": "g"},
    {"code": "RM-FLUX",       "name": "Flux Solution",               "material_type": "raw",           "uom": "mL"},
    {"code": "RM-CONFORMAL",  "name": "Conformal Coating",           "material_type": "raw",           "uom": "mL"},
    {"code": "SF-POP-PCB",    "name": "Populated PCB Assembly",      "material_type": "semi_finished", "uom": "EA"},
    {"code": "PKG-ESD-BAG",   "name": "ESD Protective Bag",          "material_type": "packaging",     "uom": "EA"},
    {"code": "FG-ECB-100",    "name": "Electronic Controller Board v1", "material_type": "finished",   "uom": "EA"},
]

# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

PRODUCT = {
    "code": "FG-ECB-100",
    "name": "Electronic Controller Board v1",
    "version": "1.0",
    "product_type": "discrete",
    "description": "Series-100 electronic controller board with SMD and through-hole components",
    "uom": "EA",
}

# ---------------------------------------------------------------------------
# Bill of Material  (per unit = 1 board)
# ---------------------------------------------------------------------------

BOM_ITEMS: list[dict] = [
    {"material_code": "RM-PCB-BLANK",  "quantity": 1.0,  "uom": "EA", "position": 10, "step_sequence": 10},   # Solder Paste Application
    {"material_code": "RM-SMD-KIT",    "quantity": 1.0,  "uom": "EA", "position": 20, "step_sequence": 20},   # SMD Placement
    {"material_code": "RM-THRU-KIT",   "quantity": 1.0,  "uom": "EA", "position": 30, "step_sequence": 50},   # Through-Hole & Conformal Coat
    {"material_code": "RM-SOLDER-PST", "quantity": 5.0,  "uom": "g",  "position": 40, "step_sequence": 10},   # Solder Paste Application
    {"material_code": "RM-FLUX",       "quantity": 2.0,  "uom": "mL", "position": 50, "step_sequence": 50},   # Through-Hole & Conformal Coat
    {"material_code": "RM-CONFORMAL",  "quantity": 3.0,  "uom": "mL", "position": 60, "step_sequence": 50},   # Through-Hole & Conformal Coat
    {"material_code": "SF-POP-PCB",    "quantity": 1.0,  "uom": "EA", "position": 70},                         # no step — intermediate/output
    {"material_code": "PKG-ESD-BAG",   "quantity": 1.0,  "uom": "EA", "position": 80},                         # no step — final packaging
]

# ---------------------------------------------------------------------------
# Dispositions (top-level entities)
# ---------------------------------------------------------------------------

DISPOSITIONS: list[dict] = [
    {"code": "E-START",      "name": "Start",           "description": "Initial entry into the SMT route",      "category": "route"},
    {"code": "E-PASS-SMD",   "name": "Pass to SMD",     "description": "Advance to SMD placement",              "category": "route"},
    {"code": "E-PASS-REFL",  "name": "Pass to Reflow",  "description": "Advance to reflow soldering",           "category": "route"},
    {"code": "E-PASS-AOI",   "name": "Pass to AOI",     "description": "Advance to automated optical inspection","category": "route"},
    {"code": "E-AOI-PASS",   "name": "AOI Pass",        "description": "AOI inspection passed",                 "category": "route"},
    {"code": "E-TH-PASS",    "name": "TH Pass",         "description": "Through-hole step passed",              "category": "route"},
    {"code": "E-REWORK",     "name": "Rework",          "description": "Send to rework station",                "category": "route"},
    {"code": "E-ESCALATE",   "name": "Escalate",        "description": "Escalate to Material Review Board",     "category": "hold"},
]

# ---------------------------------------------------------------------------
# Route Steps
# ---------------------------------------------------------------------------

ROUTE_NAME = "SMT Assembly Line"

STEPS: list[dict] = [
    {
        "sequence": 10,
        "name": "Solder Paste Application",
        "step_type": "production",
        "work_cell_code": "WC-PASTE",
        "expected_cycle_time_sec": 30.0,
        "erp_operation_number": "0010",
        "disposition_code": "E-START",
    },
    {
        "sequence": 20,
        "name": "SMD Placement",
        "step_type": "production",
        "work_cell_code": "WC-PLACE",
        "expected_cycle_time_sec": 45.0,
        "erp_operation_number": "0020",
        "disposition_code": "E-PASS-SMD",
    },
    {
        "sequence": 30,
        "name": "Reflow Soldering",
        "step_type": "production",
        "work_cell_code": "WC-REFLOW",
        "expected_cycle_time_sec": 180.0,
        "erp_operation_number": "0030",
        "disposition_code": "E-PASS-REFL",
    },
    {
        "sequence": 40,
        "name": "Automated Optical Inspection",
        "step_type": "inspection",
        "work_cell_code": "WC-AOI",
        "expected_cycle_time_sec": 20.0,
        "erp_operation_number": "0040",
        "disposition_code": "E-PASS-AOI",
    },
    {
        "sequence": 50,
        "name": "Through-Hole & Conformal Coat",
        "step_type": "production",
        "work_cell_code": "WC-THT",
        "expected_cycle_time_sec": 120.0,
        "erp_operation_number": "0050",
        "disposition_code": "E-AOI-PASS",
    },
    {
        "sequence": 60,
        "name": "Functional Test",
        "step_type": "inspection",
        "work_cell_code": "WC-TEST",
        "expected_cycle_time_sec": 60.0,
        "erp_operation_number": "0060",
        "disposition_code": "E-TH-PASS",
    },
    {
        "sequence": 70,
        "name": "Rework Station",
        "step_type": "rework",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 300.0,
        "erp_operation_number": "0070",
        "disposition_code": "E-REWORK",
    },
    {
        "sequence": 80,
        "name": "MRB Review",
        "step_type": "mrb",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0080",
        "disposition_code": "E-ESCALATE",
    },
]

# ---------------------------------------------------------------------------
# Step Transitions  (graph routing)
#
# Keyed by (from_sequence, to_sequence) with condition metadata.
# ---------------------------------------------------------------------------

TRANSITIONS: list[dict] = [
    # Paste → SMD Placement (always)
    {"from_seq": 10, "to_seq": 20, "condition": "always",      "priority": 0,  "is_default": True,  "label": None},
    # SMD → Reflow (always)
    {"from_seq": 20, "to_seq": 30, "condition": "always",      "priority": 0,  "is_default": True,  "label": None},
    # Reflow → AOI (always)
    {"from_seq": 30, "to_seq": 40, "condition": "always",      "priority": 0,  "is_default": True,  "label": None},
    # AOI → TH & Coat (on_pass)
    {"from_seq": 40, "to_seq": 50, "condition": "on_pass",     "priority": 10, "is_default": True,  "label": "AOI Passed"},
    # AOI → Rework (on_fail)
    {"from_seq": 40, "to_seq": 70, "condition": "on_fail",     "priority": 10, "is_default": False, "label": "AOI Failed — Rework"},
    # AOI → MRB (on_rework — escalation for repeated failure)
    {"from_seq": 40, "to_seq": 80, "condition": "on_rework",   "priority": 20, "is_default": False, "label": "Repeat Fail — MRB"},
    # TH & Coat → Functional Test (on_pass)
    {"from_seq": 50, "to_seq": 60, "condition": "on_pass",     "priority": 0,  "is_default": True,  "label": "Passed"},
    # TH & Coat → Rework (on_fail)
    {"from_seq": 50, "to_seq": 70, "condition": "on_fail",     "priority": 10, "is_default": False, "label": "Failed — Rework"},
    # TH & Coat → MRB (on_rework — escalation for repeated failure)
    {"from_seq": 50, "to_seq": 80, "condition": "on_rework",   "priority": 20, "is_default": False, "label": "Repeat Fail — MRB"},
    # Functional Test → Rework (on_fail)
    {"from_seq": 60, "to_seq": 70, "condition": "on_fail",     "priority": 10, "is_default": False, "label": "Func Test Failed — Rework"},
    # Functional Test → MRB (on_rework — escalation for repeated failure)
    {"from_seq": 60, "to_seq": 80, "condition": "on_rework",   "priority": 20, "is_default": False, "label": "Repeat Fail — MRB"},
    # Rework → AOI (rework loop back to inspection)
    {"from_seq": 70, "to_seq": 40, "condition": "always",      "priority": 0,  "is_default": True,  "label": "Return to AOI"},
    # MRB → Rework (disposition: return to rework)
    {"from_seq": 80, "to_seq": 70, "condition": "disposition",  "priority": 10, "is_default": False, "label": "Return to Rework"},
]

# ---------------------------------------------------------------------------
# Step Parameters  (recipe / spec targets)
# ---------------------------------------------------------------------------

STEP_PARAMS: dict[int, list[dict]] = {
    10: [  # Solder Paste Application
        {"name": "Squeegee Speed",    "data_type": "numeric", "target_value": "60",   "lower_limit": "40",   "upper_limit": "80",   "uom": "mm/s", "is_required": True},
        {"name": "Squeegee Pressure", "data_type": "numeric", "target_value": "5.0",  "lower_limit": "3.0",  "upper_limit": "7.0",  "uom": "kPa",  "is_required": True},
        {"name": "Stencil Gap",       "data_type": "numeric", "target_value": "0.0",  "lower_limit": "0.0",  "upper_limit": "0.05", "uom": "mm",   "is_required": True},
    ],
    20: [  # SMD Placement
        {"name": "Placement Speed",   "data_type": "numeric", "target_value": "15000","lower_limit": "10000","upper_limit": "20000","uom": "cph",   "is_required": True},
        {"name": "Nozzle Vacuum",     "data_type": "numeric", "target_value": "60",   "lower_limit": "50",   "upper_limit": "70",   "uom": "kPa",   "is_required": True},
        {"name": "Vision Tolerance",  "data_type": "numeric", "target_value": "0.05", "lower_limit": "0.02", "upper_limit": "0.10", "uom": "mm",    "is_required": True},
    ],
    30: [  # Reflow Soldering
        {"name": "Zone 1 Temp",       "data_type": "numeric", "target_value": "150",  "lower_limit": "140",  "upper_limit": "160",  "uom": "°C",     "is_required": True},
        {"name": "Zone 2 Temp",       "data_type": "numeric", "target_value": "180",  "lower_limit": "170",  "upper_limit": "190",  "uom": "°C",     "is_required": True},
        {"name": "Zone 3 Temp",       "data_type": "numeric", "target_value": "230",  "lower_limit": "220",  "upper_limit": "240",  "uom": "°C",     "is_required": True},
        {"name": "Zone 4 Temp",       "data_type": "numeric", "target_value": "245",  "lower_limit": "240",  "upper_limit": "250",  "uom": "°C",     "is_required": True},
        {"name": "Zone 5 Temp",       "data_type": "numeric", "target_value": "200",  "lower_limit": "190",  "upper_limit": "210",  "uom": "°C",     "is_required": True},
        {"name": "Conveyor Speed",    "data_type": "numeric", "target_value": "800",  "lower_limit": "700",  "upper_limit": "900",  "uom": "mm/min", "is_required": True},
    ],
    40: [  # Automated Optical Inspection
        {"name": "Resolution",        "data_type": "numeric", "target_value": "15",   "lower_limit": "10",   "upper_limit": "20",   "uom": "µm",  "is_required": True},
        {"name": "Inspection Time",   "data_type": "numeric", "target_value": "8",    "lower_limit": "5",    "upper_limit": "15",   "uom": "s",   "is_required": True},
        {"name": "Defect Threshold",  "data_type": "numeric", "target_value": "0",    "lower_limit": "0",    "upper_limit": "3",    "uom": "count","is_required": True},
    ],
    50: [  # Through-Hole & Conformal Coat
        {"name": "Wave Temp",         "data_type": "numeric", "target_value": "260",  "lower_limit": "250",  "upper_limit": "270",  "uom": "°C",  "is_required": True},
        {"name": "Wave Speed",        "data_type": "numeric", "target_value": "1200", "lower_limit": "1000", "upper_limit": "1400", "uom": "mm/s","is_required": True},
        {"name": "Coat Thickness",    "data_type": "numeric", "target_value": "50",   "lower_limit": "25",   "upper_limit": "75",   "uom": "µm",  "is_required": True},
        {"name": "Cure Time",         "data_type": "numeric", "target_value": "300",  "lower_limit": "240",  "upper_limit": "360",  "uom": "s",   "is_required": True},
    ],
    60: [  # Functional Test
        {"name": "Supply Voltage",    "data_type": "numeric", "target_value": "5.0",  "lower_limit": "4.9",  "upper_limit": "5.1",  "uom": "V",   "is_required": True},
        {"name": "Current Limit",     "data_type": "numeric", "target_value": "500",  "lower_limit": "0",    "upper_limit": "800",  "uom": "mA",  "is_required": True},
        {"name": "Test Duration",     "data_type": "numeric", "target_value": "30",   "lower_limit": "20",   "upper_limit": "45",   "uom": "s",   "is_required": True},
    ],
    70: [  # Rework Station
        {"name": "Rework Action",     "data_type": "enum",    "target_value": None,   "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
        {"name": "Rework Notes",      "data_type": "string",  "target_value": None,   "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
    ],
    80: [  # MRB Review
        {"name": "Disposition",       "data_type": "enum",    "target_value": None,   "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
        {"name": "Review Notes",      "data_type": "string",  "target_value": None,   "lower_limit": None,   "upper_limit": None,   "uom": None,  "is_required": True},
    ],
}

# ---------------------------------------------------------------------------
# Data Collection Definitions  (actual measurement collection)
# ---------------------------------------------------------------------------

DATA_DEFS: dict[int, list[dict]] = {
    10: [
        {"code": "ECB-PASTE-SPEED",  "name": "Squeegee Speed",    "data_type": "numeric", "source": "equipment", "lower_limit": 40.0,   "upper_limit": 80.0,   "uom": "mm/s", "is_required": True},
        {"code": "ECB-PASTE-PRESS",  "name": "Squeegee Pressure", "data_type": "numeric", "source": "equipment", "lower_limit": 3.0,    "upper_limit": 7.0,    "uom": "kPa",  "is_required": True},
        {"code": "ECB-PASTE-GAP",    "name": "Stencil Gap",       "data_type": "numeric", "source": "sensor",    "lower_limit": 0.0,    "upper_limit": 0.05,   "uom": "mm",   "is_required": True},
    ],
    20: [
        {"code": "ECB-PNP-SPEED",    "name": "Placement Speed",   "data_type": "numeric", "source": "equipment", "lower_limit": 10000.0,"upper_limit": 20000.0,"uom": "cph",   "is_required": True},
        {"code": "ECB-PNP-VAC",      "name": "Nozzle Vacuum",     "data_type": "numeric", "source": "equipment", "lower_limit": 50.0,   "upper_limit": 70.0,   "uom": "kPa",   "is_required": True},
        {"code": "ECB-PNP-VIS",      "name": "Vision Tolerance",  "data_type": "numeric", "source": "equipment", "lower_limit": 0.02,   "upper_limit": 0.10,   "uom": "mm",    "is_required": True},
    ],
    30: [
        {"code": "ECB-RF-Z1",        "name": "Zone 1 Temperature","data_type": "numeric", "source": "sensor",    "lower_limit": 140.0,  "upper_limit": 160.0,  "uom": "°C",     "is_required": True},
        {"code": "ECB-RF-Z2",        "name": "Zone 2 Temperature","data_type": "numeric", "source": "sensor",    "lower_limit": 170.0,  "upper_limit": 190.0,  "uom": "°C",     "is_required": True},
        {"code": "ECB-RF-Z3",        "name": "Zone 3 Temperature","data_type": "numeric", "source": "sensor",    "lower_limit": 220.0,  "upper_limit": 240.0,  "uom": "°C",     "is_required": True},
        {"code": "ECB-RF-Z4",        "name": "Zone 4 Temperature","data_type": "numeric", "source": "sensor",    "lower_limit": 240.0,  "upper_limit": 250.0,  "uom": "°C",     "is_required": True},
        {"code": "ECB-RF-Z5",        "name": "Zone 5 Temperature","data_type": "numeric", "source": "sensor",    "lower_limit": 190.0,  "upper_limit": 210.0,  "uom": "°C",     "is_required": True},
        {"code": "ECB-RF-CONV",      "name": "Conveyor Speed",    "data_type": "numeric", "source": "equipment", "lower_limit": 700.0,  "upper_limit": 900.0,  "uom": "mm/min", "is_required": True},
    ],
    40: [
        {"code": "ECB-AOI-RES",      "name": "Resolution",           "data_type": "numeric", "source": "equipment", "lower_limit": 10.0,  "upper_limit": 20.0,  "uom": "µm",   "is_required": True},
        {"code": "ECB-AOI-TIME",     "name": "Inspection Time",      "data_type": "numeric", "source": "equipment", "lower_limit": 5.0,   "upper_limit": 15.0,  "uom": "s",    "is_required": True},
        {"code": "ECB-AOI-DEF",      "name": "Defect Count",         "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,   "upper_limit": 3.0,   "uom": "count","is_required": True},
    ],
    50: [
        {"code": "ECB-TH-WAVETEMP",  "name": "Wave Solder Temp",     "data_type": "numeric", "source": "equipment", "lower_limit": 250.0, "upper_limit": 270.0, "uom": "°C",  "is_required": True},
        {"code": "ECB-TH-WAVESPD",   "name": "Wave Speed",           "data_type": "numeric", "source": "equipment", "lower_limit": 1000.0,"upper_limit": 1400.0,"uom": "mm/s","is_required": True},
        {"code": "ECB-TH-COAT",      "name": "Conformal Coat Thickness","data_type": "numeric","source": "sensor",   "lower_limit": 25.0,  "upper_limit": 75.0,  "uom": "µm",  "is_required": True},
        {"code": "ECB-TH-CURE",      "name": "Cure Time",            "data_type": "numeric", "source": "equipment", "lower_limit": 240.0, "upper_limit": 360.0, "uom": "s",   "is_required": True},
    ],
    60: [
        {"code": "ECB-FCT-VOLT",     "name": "Measured Voltage",     "data_type": "numeric", "source": "equipment", "lower_limit": 4.9,   "upper_limit": 5.1,   "uom": "V",   "is_required": True},
        {"code": "ECB-FCT-CURR",     "name": "Measured Current",     "data_type": "numeric", "source": "equipment", "lower_limit": 0.0,   "upper_limit": 800.0, "uom": "mA",  "is_required": True},
        {"code": "ECB-FCT-DUR",      "name": "Actual Test Duration",  "data_type": "numeric", "source": "equipment", "lower_limit": 20.0,  "upper_limit": 45.0,  "uom": "s",   "is_required": True},
        {"code": "ECB-FCT-IO",       "name": "I/O Channels OK",      "data_type": "boolean", "source": "equipment", "lower_limit": None,  "upper_limit": None,  "uom": None,  "is_required": True},
        {"code": "ECB-FCT-FW",       "name": "Firmware Checksum OK",  "data_type": "boolean", "source": "equipment", "lower_limit": None,  "upper_limit": None,  "uom": None,  "is_required": True},
    ],
    70: [
        {"code": "ECB-RW-ACTION",    "name": "Rework Action Taken",  "data_type": "enum",    "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None,  "is_required": True,
         "enum_values": "re_solder,replace_component,re_coat,jumper_wire,other"},
        {"code": "ECB-RW-NOTES",     "name": "Rework Notes",         "data_type": "string",  "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None,  "is_required": True},
    ],
    80: [
        {"code": "ECB-MRB-DISP",     "name": "Disposition",          "data_type": "enum",    "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None,  "is_required": True,
         "enum_values": "return_to_rework,scrap,ship_as_is"},
        {"code": "ECB-MRB-NOTES",    "name": "Review Notes",         "data_type": "string",  "source": "manual",    "lower_limit": None,  "upper_limit": None,  "uom": None,  "is_required": True},
    ],
}

# ---------------------------------------------------------------------------
# Quality Test  (at Functional Test step 60)
# ---------------------------------------------------------------------------

QUALITY_TEST = {
    "code": "ECB-FCT-BOARD",
    "name": "Board Functional Test",
    "test_type": "inline",
    "parameters": {
        "description": "Supply voltage, current draw, I/O channel response, firmware checksum verification",
        "pass_criteria": "Voltage within +/-0.1V, current under 800mA, all I/O OK, firmware checksum match",
    },
}

# ---------------------------------------------------------------------------
# Production Orders  (removed — create via Production Orders page in ERP Sim)
# ---------------------------------------------------------------------------

ORDERS: list[dict] = []

SERIAL_TEMPLATE = "SN-{order}-{seq:05d}"

# ---------------------------------------------------------------------------
# Physical Model  (ISA-95 hierarchy)
# ---------------------------------------------------------------------------

SITE = {"code": "APEX-ELEC",  "name": "Apex Electronics Factory",  "description": "Electronic controller board manufacturing facility", "timezone": "America/Chicago"}
AREA = {"code": "PCBA-AREA",  "name": "PCB Assembly Area",         "description": "Surface-mount and through-hole assembly"}
LINE = {"code": "LINE-SMT-01","name": "SMT Assembly Line 1",       "description": "High-mix SMT line with dual pick-and-place"}

WORK_CELLS: list[dict] = [
    {"code": "WC-PASTE",  "name": "Paste Application Cell",   "description": "Stencil printer for solder paste"},
    {"code": "WC-PLACE",  "name": "Component Placement Cell",  "description": "Pick-and-place SMD mounting"},
    {"code": "WC-REFLOW", "name": "Reflow Oven Cell",          "description": "5-zone convection reflow soldering"},
    {"code": "WC-AOI",    "name": "Optical Inspection Cell",   "description": "Automated optical inspection station"},
    {"code": "WC-THT",    "name": "Through-Hole & Coating Cell","description": "Wave solder and conformal coating"},
    {"code": "WC-TEST",   "name": "Functional Test Cell",      "description": "In-circuit and functional test"},
    {"code": "WC-REWORK", "name": "Rework Station Cell",       "description": "Manual rework and MRB review bench"},
]

EQUIPMENT: list[dict] = [
    {"code": "SP-200",   "name": "Stencil Printer SP-200",   "work_cell_code": "WC-PASTE",  "state_model": "packml",   "max_queue_depth": 1},
    {"code": "PNP-800A", "name": "Pick-and-Place PNP-800A",  "work_cell_code": "WC-PLACE",  "state_model": "packml",   "max_queue_depth": 2},
    {"code": "PNP-800B", "name": "Pick-and-Place PNP-800B",  "work_cell_code": "WC-PLACE",  "state_model": "packml",   "max_queue_depth": 2},
    {"code": "RO-500",   "name": "5-Zone Reflow Oven",       "work_cell_code": "WC-REFLOW", "state_model": "semi_e10", "max_queue_depth": 5},
    {"code": "AOI-300",  "name": "AOI Camera System",        "work_cell_code": "WC-AOI",    "state_model": "packml",   "max_queue_depth": 1},
    {"code": "WS-100",   "name": "Wave Solder + Coat Station","work_cell_code": "WC-THT",   "state_model": "semi_e10", "max_queue_depth": 1},
    {"code": "FCT-200",  "name": "Functional Test Fixture",  "work_cell_code": "WC-TEST",   "state_model": "semi_e10", "max_queue_depth": 1},
    {"code": "RW-BENCH", "name": "Rework Bench",             "work_cell_code": "WC-REWORK", "state_model": "semi_e10", "max_queue_depth": 3},
]

# Equipment-material assignments  (design speed in units/hr, target OEE %)
EQUIPMENT_MATERIALS: list[dict] = [
    {"equipment_code": "SP-200",   "material_code": "FG-ECB-100", "design_speed": 120.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 90.0},
    {"equipment_code": "PNP-800A", "material_code": "FG-ECB-100", "design_speed": 80.0,  "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "PNP-800B", "material_code": "FG-ECB-100", "design_speed": 80.0,  "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 92.0},
    {"equipment_code": "RO-500",   "material_code": "FG-ECB-100", "design_speed": 200.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 95.0},
    {"equipment_code": "AOI-300",  "material_code": "FG-ECB-100", "design_speed": 180.0, "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 98.0},
    {"equipment_code": "WS-100",   "material_code": "FG-ECB-100", "design_speed": 60.0,  "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 88.0},
    {"equipment_code": "FCT-200",  "material_code": "FG-ECB-100", "design_speed": 60.0,  "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 95.0},
    {"equipment_code": "RW-BENCH", "material_code": "FG-ECB-100", "design_speed": 10.0,  "design_speed_uom": "EA", "reject_uom": "EA", "target_oee": 70.0},
]

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Equipment Classes & Properties
# ---------------------------------------------------------------------------

EQUIPMENT_CLASSES: list[dict] = [
    {"code": "PRINTER",     "name": "Stencil Printer",   "description": "Solder-paste stencil printing equipment"},
    {"code": "PLACEMENT",   "name": "Pick-and-Place",    "description": "SMT component placement machine"},
    {"code": "FEEDER_BANK", "name": "Feeder Bank",       "description": "Component feeder bank that loads tape-and-reel into a pick-and-place"},
    {"code": "OVEN",        "name": "Reflow Oven",       "description": "Convection / IR reflow soldering oven"},
    {"code": "CONVEYOR",    "name": "Conveyor",          "description": "Board transport conveyor linking placement to reflow"},
    {"code": "INSPECTION",  "name": "Inspection System", "description": "Automated optical / X-ray inspection"},
    {"code": "WAVE_SOLDER", "name": "Wave Solder",       "description": "Wave soldering and conformal coating"},
    {"code": "TESTER",      "name": "Functional Tester", "description": "ICT / FCT test fixture"},
    {"code": "FIXTURE",     "name": "Test Fixture",      "description": "Product-specific mechanical/electrical test fixture"},
    {"code": "MANUAL",      "name": "Manual Station",    "description": "Manual rework / repair bench"},
]

EQUIPMENT_CLASS_PROPERTIES: list[dict] = [
    # Placement
    {"class_code": "PLACEMENT",  "name": "max_cph",       "data_type": "float",  "uom_id": "cph",  "default_value": "80000",   "description": "Max components per hour"},
    {"class_code": "PLACEMENT",  "name": "feeder_slots",  "data_type": "int",    "uom_id": None,   "default_value": "120",     "description": "Number of feeder slots"},
    # Oven
    {"class_code": "OVEN",       "name": "zone_count",    "data_type": "int",    "uom_id": None,   "default_value": "5",       "description": "Number of heating zones"},
    {"class_code": "OVEN",       "name": "max_temp_c",    "data_type": "float",  "uom_id": "°C",   "default_value": "260",     "description": "Max zone temperature"},
    # Printer
    {"class_code": "PRINTER",    "name": "max_board_size", "data_type": "string", "uom_id": "mm",  "default_value": "460x305", "description": "Max PCB size (LxW)"},
]

# Maps equipment code → equipment class code
EQUIPMENT_CLASS_MAP: dict[str, str] = {
    "SP-200":   "PRINTER",
    "PNP-800A": "PLACEMENT",
    "PNP-800B": "PLACEMENT",
    "RO-500":   "OVEN",
    "AOI-300":  "INSPECTION",
    "WS-100":   "WAVE_SOLDER",
    "FCT-200":  "TESTER",
    "RW-BENCH": "MANUAL",
}

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Process Segment → Equipment Class (dispatch constraint)
# ---------------------------------------------------------------------------
# Each process segment declares what class of equipment it needs; the
# dispatcher uses this to narrow the candidate set before applying
# SegmentEquipmentRequirement preferences below.

STEP_EQUIPMENT_CLASS: dict[int, str] = {
    10: "PRINTER",      # Solder Paste Application
    20: "PLACEMENT",    # SMD Placement
    30: "OVEN",         # Reflow Soldering
    40: "INSPECTION",   # Automated Optical Inspection
    50: "WAVE_SOLDER",  # Through-Hole & Conformal Coat
    60: "TESTER",       # Functional Test
    70: "MANUAL",       # Rework Station
    80: "MANUAL",       # MRB Review
}

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Segment Equipment Requirements
# ---------------------------------------------------------------------------
# Specific-equipment preferences that augment the class-level constraint above.
# use_type: "required" | "preferred" | "alternate"

SEGMENT_EQUIPMENT_REQUIREMENTS: list[dict] = [
    # ── Class-level multi-equipment requirements (ISA-95 Part 2
    # EquipmentSegmentSpecification).  Each step's primary class is
    # already captured on ProcessSegment.equipment_class_id via
    # STEP_EQUIPMENT_CLASS above; these entries declare the *additional*
    # equipment classes the step needs at the same time.  Dispatch ANDs
    # them together.
    #
    # SMD Placement needs 1× PLACEMENT (primary) + 1× FEEDER_BANK
    {"step_sequence": 20, "equipment_class_code": "FEEDER_BANK", "use_type": "required",
     "description": "Tape-and-reel feeder bank loaded with SMD kit"},
    # Reflow Soldering needs 1× OVEN (primary) + 1× CONVEYOR
    {"step_sequence": 30, "equipment_class_code": "CONVEYOR",    "use_type": "required",
     "description": "Inline conveyor feeding the reflow oven"},
    # Functional Test needs 1× TESTER (primary) + 1× FIXTURE
    {"step_sequence": 60, "equipment_class_code": "FIXTURE",     "use_type": "required",
     "description": "Product-specific FCT test fixture"},

    # ── Specific-equipment preferences augmenting the class constraint.
    # SMD Placement: dual pick-and-place — either is acceptable
    {"step_sequence": 20, "equipment_code": "PNP-800A", "use_type": "preferred", "description": "Primary pick-and-place"},
    {"step_sequence": 20, "equipment_code": "PNP-800B", "use_type": "alternate", "description": "Secondary pick-and-place (load balancing)"},
    # Wave-solder + conformal coat — only one line, must use it
    {"step_sequence": 50, "equipment_code": "WS-100",   "use_type": "required",  "description": "Only wave-solder + conformal coat line"},
    # Functional Test — calibrated tester required (fixture-class above covers the fixture)
    {"step_sequence": 60, "equipment_code": "FCT-200",  "use_type": "required",  "description": "Calibrated FCT tester"},
    # Rework and MRB share the same bench
    {"step_sequence": 70, "equipment_code": "RW-BENCH", "use_type": "required",  "description": "Manual rework bench"},
    {"step_sequence": 80, "equipment_code": "RW-BENCH", "use_type": "required",  "description": "MRB review at rework bench"},
]

# ---------------------------------------------------------------------------
# ISA-95 Part 2: Segment Material Requirements
# ---------------------------------------------------------------------------
# Declarative per-segment consumed/produced materials.  Complements the
# product-specific BillOfMaterial (BOMItem) by describing the segment's
# material behavior independent of any particular product.

SEGMENT_MATERIAL_REQUIREMENTS: list[dict] = [
    # 10 — Solder Paste Application
    {"step_sequence": 10, "material_code": "RM-PCB-BLANK",  "quantity": 1.0, "uom": "EA", "material_use": "consumed", "position": 10, "description": "Bare PCB blank"},
    {"step_sequence": 10, "material_code": "RM-SOLDER-PST", "quantity": 5.0, "uom": "g",  "material_use": "consumed", "position": 20, "description": "Solder paste deposit"},
    # 20 — SMD Placement
    {"step_sequence": 20, "material_code": "RM-SMD-KIT",    "quantity": 1.0, "uom": "EA", "material_use": "consumed", "position": 10, "description": "SMD component kit"},
    # 30 — Reflow Soldering
    {"step_sequence": 30, "material_code": "SF-POP-PCB",    "quantity": 1.0, "uom": "EA", "material_use": "produced", "position": 10, "description": "Populated PCB (SMD only)"},
    # 50 — Through-Hole & Conformal Coat
    {"step_sequence": 50, "material_code": "RM-THRU-KIT",   "quantity": 1.0, "uom": "EA", "material_use": "consumed", "position": 10, "description": "Through-hole components"},
    {"step_sequence": 50, "material_code": "RM-FLUX",       "quantity": 2.0, "uom": "mL", "material_use": "consumed", "position": 20, "description": "Wave-solder flux"},
    {"step_sequence": 50, "material_code": "RM-CONFORMAL",  "quantity": 3.0, "uom": "mL", "material_use": "consumed", "position": 30, "description": "Conformal coating"},
    # 60 — Functional Test: produces the finished ECB, ESD bag applied
    {"step_sequence": 60, "material_code": "FG-ECB-100",    "quantity": 1.0, "uom": "EA", "material_use": "produced", "position": 10, "description": "Finished Electronic Controller Board"},
    {"step_sequence": 60, "material_code": "PKG-ESD-BAG",   "quantity": 1.0, "uom": "EA", "material_use": "consumed", "position": 20, "description": "ESD protective bag"},
]

# ---------------------------------------------------------------------------
# OperationsDefinition ↔ Material assignments (route-level raw materials)
# ---------------------------------------------------------------------------
# Declares every material referenced anywhere in the SMT route.  Lets the
# ERP/MES see the full raw-material list for a route at a glance.

ROUTE_MATERIAL_ASSIGNMENTS: list[str] = [
    "RM-PCB-BLANK", "RM-SMD-KIT", "RM-THRU-KIT",
    "RM-SOLDER-PST", "RM-FLUX", "RM-CONFORMAL",
    "SF-POP-PCB", "PKG-ESD-BAG",
]

# ---------------------------------------------------------------------------
# Material Lots  (initial raw-material inventory)
# ---------------------------------------------------------------------------

MATERIAL_LOTS: list[dict] = [
    {"material_code": "RM-PCB-BLANK",  "lot_number": "LOT-PCB-2026A",  "quantity_on_hand": 2000.0,  "supplier": "PCBTech Inc."},
    {"material_code": "RM-SMD-KIT",    "lot_number": "LOT-SMD-2026A",  "quantity_on_hand": 1500.0,  "supplier": "Arrow Electronics"},
    {"material_code": "RM-THRU-KIT",   "lot_number": "LOT-THRU-2026A", "quantity_on_hand": 1500.0,  "supplier": "Digi-Key"},
    {"material_code": "RM-SOLDER-PST", "lot_number": "LOT-SLDR-2026A", "quantity_on_hand": 50000.0, "supplier": "Kester"},
    {"material_code": "RM-FLUX",       "lot_number": "LOT-FLUX-2026A", "quantity_on_hand": 20000.0, "supplier": "Kester"},
    {"material_code": "RM-CONFORMAL",  "lot_number": "LOT-CONF-2026A", "quantity_on_hand": 30000.0, "supplier": "HumiSeal"},
    {"material_code": "PKG-ESD-BAG",   "lot_number": "LOT-ESDB-2026A", "quantity_on_hand": 2500.0,  "supplier": "Desco Industries"},
]

# ---------------------------------------------------------------------------
# Storage Locations  (inventory module)
# ---------------------------------------------------------------------------

STORAGE_LOCATIONS: list[dict] = [
    {"code": "EB-RECV-01", "name": "Electronics Receiving Dock", "location_type": "receiving", "description": "Inbound goods receipt area"},
    {"code": "EB-WH-SMT",  "name": "SMT Component Warehouse",    "location_type": "storage",  "aisle": "A", "bay": "01", "tier": "01", "description": "SMD kits, paste, through-hole kits, flux, coating"},
    {"code": "EB-WH-PKG",  "name": "Packaging Warehouse",        "location_type": "storage",  "aisle": "B", "bay": "01", "tier": "01", "description": "ESD bags and shipping materials"},
    {"code": "EB-STG-01",  "name": "Line-Side Staging",          "location_type": "staging",  "description": "Pre-production staging at SMT line"},
    {"code": "EB-RIP-SMT", "name": "RIP — SMT Line",            "location_type": "rip",      "description": "Raw-and-In-Process at SMT line"},
    {"code": "EB-SHIP-01", "name": "Finished Goods Shipping",    "location_type": "shipping", "description": "Outbound ECB units"},
]

# Map raw-material codes → warehouse location they're putaway to after receipt
MATERIAL_STORAGE_MAP: dict[str, str] = {
    "RM-PCB-BLANK":  "EB-WH-SMT",
    "RM-SMD-KIT":    "EB-WH-SMT",
    "RM-THRU-KIT":   "EB-WH-SMT",
    "RM-SOLDER-PST": "EB-WH-SMT",
    "RM-FLUX":       "EB-WH-SMT",
    "RM-CONFORMAL":  "EB-WH-SMT",
    "PKG-ESD-BAG":   "EB-WH-PKG",
}

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
    {"equipment_code": "SP-200",   "equipment_class_code": "PRINTER",     "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_board_size", "value": "460x305"}]},
    {"equipment_code": "PNP-800A", "equipment_class_code": "PLACEMENT",   "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_cph", "value": "80000"}, {"property_name": "feeder_slots", "value": "120"}]},
    {"equipment_code": "PNP-800B", "equipment_class_code": "PLACEMENT",   "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "max_cph", "value": "80000"}, {"property_name": "feeder_slots", "value": "120"}]},
    {"equipment_code": "RO-500",   "equipment_class_code": "OVEN",        "capability_type": "available", "reason": "Nominal",
     "properties": [{"property_name": "zone_count", "value": "5"}, {"property_name": "max_temp_c", "value": "260"}]},
    {"equipment_code": "AOI-300",  "equipment_class_code": "INSPECTION",  "capability_type": "available", "reason": "Nominal"},
    {"equipment_code": "WS-100",   "equipment_class_code": "WAVE_SOLDER", "capability_type": "available", "reason": "Nominal"},
    {"equipment_code": "FCT-200",  "equipment_class_code": "TESTER",      "capability_type": "available", "reason": "Nominal"},
    {"equipment_code": "RW-BENCH", "equipment_class_code": "MANUAL",      "capability_type": "available", "reason": "Manual rework bench"},
]
