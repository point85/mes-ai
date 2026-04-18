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
        "input_disposition": "Start",
        "disposition_category": "route",
    },
    {
        "sequence": 20,
        "name": "SMD Placement",
        "step_type": "production",
        "work_cell_code": "WC-PLACE",
        "expected_cycle_time_sec": 45.0,
        "erp_operation_number": "0020",
        "input_disposition": "Pass to SMD",
        "disposition_category": "route",
    },
    {
        "sequence": 30,
        "name": "Reflow Soldering",
        "step_type": "production",
        "work_cell_code": "WC-REFLOW",
        "expected_cycle_time_sec": 180.0,
        "erp_operation_number": "0030",
        "input_disposition": "Pass to Reflow",
        "disposition_category": "route",
    },
    {
        "sequence": 40,
        "name": "Automated Optical Inspection",
        "step_type": "inspection",
        "work_cell_code": "WC-AOI",
        "expected_cycle_time_sec": 20.0,
        "erp_operation_number": "0040",
        "input_disposition": "Pass to AOI",
        "disposition_category": "route",
    },
    {
        "sequence": 50,
        "name": "Through-Hole & Conformal Coat",
        "step_type": "production",
        "work_cell_code": "WC-THT",
        "expected_cycle_time_sec": 120.0,
        "erp_operation_number": "0050",
        "input_disposition": "AOI Pass",
        "disposition_category": "route",
    },
    {
        "sequence": 60,
        "name": "Functional Test",
        "step_type": "inspection",
        "work_cell_code": "WC-TEST",
        "expected_cycle_time_sec": 60.0,
        "erp_operation_number": "0060",
        "input_disposition": "TH Pass",
        "disposition_category": "route",
    },
    {
        "sequence": 70,
        "name": "Rework Station",
        "step_type": "rework",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 300.0,
        "erp_operation_number": "0070",
        "input_disposition": "Rework",
        "disposition_category": "route",
    },
    {
        "sequence": 80,
        "name": "MRB Review",
        "step_type": "mrb",
        "work_cell_code": "WC-REWORK",
        "expected_cycle_time_sec": 600.0,
        "erp_operation_number": "0080",
        "input_disposition": "Escalate",
        "disposition_category": "hold",
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
    {"code": "WC-PASTE",  "name": "Paste Application Cell",   "wc_type": "automated", "description": "Stencil printer for solder paste"},
    {"code": "WC-PLACE",  "name": "Component Placement Cell",  "wc_type": "automated", "description": "Pick-and-place SMD mounting"},
    {"code": "WC-REFLOW", "name": "Reflow Oven Cell",          "wc_type": "automated", "description": "5-zone convection reflow soldering"},
    {"code": "WC-AOI",    "name": "Optical Inspection Cell",   "wc_type": "automated", "description": "Automated optical inspection station"},
    {"code": "WC-THT",    "name": "Through-Hole & Coating Cell","wc_type": "semi_auto", "description": "Wave solder and conformal coating"},
    {"code": "WC-TEST",   "name": "Functional Test Cell",      "wc_type": "automated", "description": "In-circuit and functional test"},
    {"code": "WC-REWORK", "name": "Rework Station Cell",       "wc_type": "manual",    "description": "Manual rework and MRB review bench"},
]

EQUIPMENT: list[dict] = [
    {"code": "SP-200",   "name": "Stencil Printer SP-200",   "work_cell_code": "WC-PASTE",  "equipment_type": "printer",     "state_model": "packml",   "max_queue_depth": 1},
    {"code": "PNP-800A", "name": "Pick-and-Place PNP-800A",  "work_cell_code": "WC-PLACE",  "equipment_type": "placement",   "state_model": "packml",   "max_queue_depth": 2},
    {"code": "PNP-800B", "name": "Pick-and-Place PNP-800B",  "work_cell_code": "WC-PLACE",  "equipment_type": "placement",   "state_model": "packml",   "max_queue_depth": 2},
    {"code": "RO-500",   "name": "5-Zone Reflow Oven",       "work_cell_code": "WC-REFLOW", "equipment_type": "oven",        "state_model": "semi_e10", "max_queue_depth": 5},
    {"code": "AOI-300",  "name": "AOI Camera System",        "work_cell_code": "WC-AOI",    "equipment_type": "inspection",  "state_model": "packml",   "max_queue_depth": 1},
    {"code": "WS-100",   "name": "Wave Solder + Coat Station","work_cell_code": "WC-THT",   "equipment_type": "wave_solder", "state_model": "semi_e10", "max_queue_depth": 1},
    {"code": "FCT-200",  "name": "Functional Test Fixture",  "work_cell_code": "WC-TEST",   "equipment_type": "tester",      "state_model": "semi_e10", "max_queue_depth": 1},
    {"code": "RW-BENCH", "name": "Rework Bench",             "work_cell_code": "WC-REWORK", "equipment_type": "manual",      "state_model": "semi_e10", "max_queue_depth": 3},
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
