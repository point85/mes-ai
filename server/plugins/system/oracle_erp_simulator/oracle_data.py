"""
Oracle Cloud ERP Simulator: realistic Oracle Fusion REST fixture data.

Every record uses genuine Oracle Cloud field names as they appear in the
Oracle REST API (Manufacturing, Inventory, Product Management modules).
The OracleTransformLayer in ``mes.adapters.erp.oracle.transform`` maps
these into MES canonical DTOs.

Organisational hierarchy
~~~~~~~~~~~~~~~~~~~~~~~~
- Business Unit: BU_MANUFACTURING — "Global Manufacturing BU"
- Organization (Inventory Org): ORG_MAIN — "Main Manufacturing Org"
- Subinventory: MAIN_STORES — "Main Warehouse Stores"

Product catalogue
~~~~~~~~~~~~~~~~~
Three finished goods (FINISHED_GOOD), each with a BOM (Item Structure)
and Routing (Work Order Operations):
  FG-WIDGET-100  — Standard Widget (steel housing + PCB + screws)
  FG-WIDGET-200  — Premium Widget (aluminium housing + PCB + display + screws)
  FG-GADGET-300  — Gadget Model X (plastic case + PCB + battery + sensor)

Raw / semi-finished materials feed into those BOMs.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════
# Materials  (Oracle Inventory Items — /fscmRestApi/resources/inventoryItems)
# ═══════════════════════════════════════════════════════════════════

ORACLE_MATERIALS: list[dict] = [
    # ── Raw materials (STANDARD) ─────────────────────────────────
    {
        "ItemNumber": "RM-STEEL-1MM",
        "Description": "Carbon Steel Sheet 1 mm",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "KG",
        "LongDescription": "Cold-rolled carbon steel sheet, 1 mm thickness",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100001,
    },
    {
        "ItemNumber": "RM-ALUM-2MM",
        "Description": "Aluminium Sheet 2 mm",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "KG",
        "LongDescription": "6061-T6 aluminium alloy sheet, 2 mm thickness",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100002,
    },
    {
        "ItemNumber": "RM-ABS-PELLET",
        "Description": "ABS Plastic Pellets",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "KG",
        "LongDescription": "Injection-grade ABS resin pellets",
        "ShelfLifeDays": 730,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100003,
    },
    {
        "ItemNumber": "RM-SCREW-M3",
        "Description": "M3x10 Machine Screw SS",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "M3 x 10 mm stainless steel pan-head machine screw",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100004,
    },
    {
        "ItemNumber": "RM-SCREW-M4",
        "Description": "M4x12 Machine Screw SS",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "M4 x 12 mm stainless steel pan-head machine screw",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100005,
    },
    {
        "ItemNumber": "RM-COPPER-WIRE",
        "Description": "Copper Wire 0.5 mm",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "M",
        "LongDescription": "Enamelled copper magnet wire, 0.5 mm diameter",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100006,
    },
    {
        "ItemNumber": "RM-RESISTOR-10K",
        "Description": "Resistor 10 kΩ 0805",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "SMD resistor 10 kΩ ±1 %, 0805 package",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100007,
    },
    {
        "ItemNumber": "RM-CAP-100UF",
        "Description": "Capacitor 100 µF 25 V",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Electrolytic capacitor 100 µF 25 V",
        "ShelfLifeDays": 1825,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100008,
    },
    {
        "ItemNumber": "RM-DISPLAY-OLED",
        "Description": "OLED Display Module 1.3 in",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "128×64 OLED display module, I2C interface",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100009,
    },
    {
        "ItemNumber": "RM-BATTERY-LIPO",
        "Description": "LiPo Battery 3.7 V 2000 mAh",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Lithium polymer rechargeable battery, 3.7 V / 2000 mAh",
        "ShelfLifeDays": 365,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100010,
    },
    {
        "ItemNumber": "RM-SENSOR-TEMP",
        "Description": "Temperature Sensor NTC 10 kΩ",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "NTC thermistor 10 kΩ ±1 %, waterproof probe",
        "ShelfLifeDays": None,
        "ItemClass": "Raw Material",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100011,
    },
    {
        "ItemNumber": "RM-LABEL-PROD",
        "Description": "Product Label 50×30 mm",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Self-adhesive product identification label",
        "ShelfLifeDays": None,
        "ItemClass": "Packaging",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100012,
    },
    {
        "ItemNumber": "RM-BOX-SM",
        "Description": "Corrugated Box Small",
        "ItemType": "STANDARD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Single-wall corrugated shipping box 200×150×100 mm",
        "ShelfLifeDays": None,
        "ItemClass": "Packaging",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100013,
    },

    # ── Semi-finished materials (SUBASSEMBLY) ────────────────────
    {
        "ItemNumber": "SF-PCB-CTRL",
        "Description": "Main Control PCB Assembly",
        "ItemType": "SUBASSEMBLY",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Assembled and tested main control board",
        "ShelfLifeDays": None,
        "ItemClass": "WIP",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100014,
    },
    {
        "ItemNumber": "SF-HOUSING-STEEL",
        "Description": "Steel Housing Formed",
        "ItemType": "SUBASSEMBLY",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Stamped and bent carbon steel housing",
        "ShelfLifeDays": None,
        "ItemClass": "WIP",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100015,
    },
    {
        "ItemNumber": "SF-HOUSING-ALUM",
        "Description": "Aluminium Housing CNC",
        "ItemType": "SUBASSEMBLY",
        "PrimaryUOMCode": "EA",
        "LongDescription": "CNC-machined aluminium housing with anodized finish",
        "ShelfLifeDays": None,
        "ItemClass": "WIP",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100016,
    },
    {
        "ItemNumber": "SF-CASE-ABS",
        "Description": "ABS Plastic Case",
        "ItemType": "SUBASSEMBLY",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Injection-moulded ABS case (top + bottom)",
        "ShelfLifeDays": None,
        "ItemClass": "WIP",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100017,
    },

    # ── Finished goods (FINISHED_GOOD) ───────────────────────────
    {
        "ItemNumber": "FG-WIDGET-100",
        "Description": "Standard Widget 100",
        "ItemType": "FINISHED_GOOD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Standard widget w/ steel housing and control PCB",
        "ShelfLifeDays": None,
        "ItemClass": "Finished Good",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100018,
        "RevisionCode": "A",
    },
    {
        "ItemNumber": "FG-WIDGET-200",
        "Description": "Premium Widget 200",
        "ItemType": "FINISHED_GOOD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Premium widget w/ aluminium housing, display, and control PCB",
        "ShelfLifeDays": None,
        "ItemClass": "Finished Good",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100019,
        "RevisionCode": "A",
    },
    {
        "ItemNumber": "FG-GADGET-300",
        "Description": "Gadget Model 300",
        "ItemType": "FINISHED_GOOD",
        "PrimaryUOMCode": "EA",
        "LongDescription": "Portable gadget w/ ABS case, battery, sensor, and PCB",
        "ShelfLifeDays": None,
        "ItemClass": "Finished Good",
        "OrganizationCode": "ORG_MAIN",
        "InventoryItemId": 100020,
        "RevisionCode": "B",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Products  (Oracle Product Management — finished goods view)
# ═══════════════════════════════════════════════════════════════════

ORACLE_PRODUCTS: list[dict] = [
    {
        "ItemNumber": "FG-WIDGET-100",
        "Description": "Standard Widget 100",
        "ItemType": "FINISHED_GOOD",
        "RevisionCode": "A",
        "ItemStatus": "Active",
    },
    {
        "ItemNumber": "FG-WIDGET-200",
        "Description": "Premium Widget 200",
        "ItemType": "FINISHED_GOOD",
        "RevisionCode": "A",
        "ItemStatus": "Active",
    },
    {
        "ItemNumber": "FG-GADGET-300",
        "Description": "Gadget Model 300",
        "ItemType": "FINISHED_GOOD",
        "RevisionCode": "B",
        "ItemStatus": "Active",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Bills of Material  (Oracle Item Structures)
#
# Keyed by product code.  Each record uses Oracle REST field names
# with ``Component`` navigation property (like Oracle's child resources).
# ═══════════════════════════════════════════════════════════════════

ORACLE_BOMS: dict[str, list[dict]] = {
    "FG-WIDGET-100": [
        {
            "ItemNumber": "FG-WIDGET-100",
            "StructureName": "PRIMARY",
            "StructureType": "Manufacturing",
            "AlternateDesignator": "1",
            "OrganizationCode": "ORG_MAIN",
            "Component": [
                {
                    "ComponentItemNumber": "SF-HOUSING-STEEL",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "10",
                },
                {
                    "ComponentItemNumber": "SF-PCB-CTRL",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "20",
                },
                {
                    "ComponentItemNumber": "RM-SCREW-M3",
                    "ComponentQuantity": "6",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "30",
                },
                {
                    "ComponentItemNumber": "RM-LABEL-PROD",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "40",
                },
            ],
        },
    ],
    "FG-WIDGET-200": [
        {
            "ItemNumber": "FG-WIDGET-200",
            "StructureName": "PRIMARY",
            "StructureType": "Manufacturing",
            "AlternateDesignator": "1",
            "OrganizationCode": "ORG_MAIN",
            "Component": [
                {
                    "ComponentItemNumber": "SF-HOUSING-ALUM",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "10",
                },
                {
                    "ComponentItemNumber": "SF-PCB-CTRL",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "20",
                },
                {
                    "ComponentItemNumber": "RM-DISPLAY-OLED",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "30",
                },
                {
                    "ComponentItemNumber": "RM-SCREW-M4",
                    "ComponentQuantity": "8",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "40",
                },
                {
                    "ComponentItemNumber": "RM-LABEL-PROD",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "50",
                },
            ],
        },
    ],
    "FG-GADGET-300": [
        {
            "ItemNumber": "FG-GADGET-300",
            "StructureName": "PRIMARY",
            "StructureType": "Manufacturing",
            "AlternateDesignator": "1",
            "OrganizationCode": "ORG_MAIN",
            "Component": [
                {
                    "ComponentItemNumber": "SF-CASE-ABS",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "10",
                },
                {
                    "ComponentItemNumber": "SF-PCB-CTRL",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "20",
                },
                {
                    "ComponentItemNumber": "RM-BATTERY-LIPO",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "30",
                },
                {
                    "ComponentItemNumber": "RM-SENSOR-TEMP",
                    "ComponentQuantity": "2",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "40",
                },
                {
                    "ComponentItemNumber": "RM-SCREW-M3",
                    "ComponentQuantity": "4",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "50",
                },
                {
                    "ComponentItemNumber": "RM-LABEL-PROD",
                    "ComponentQuantity": "1",
                    "UOMCode": "EA",
                    "ComponentSequenceNumber": "60",
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Work Orders  (Oracle Manufacturing — /fscmRestApi/resources/workOrders)
# ═══════════════════════════════════════════════════════════════════

ORACLE_WORK_ORDERS: list[dict] = [
    {
        "WorkOrderNumber": "WO-100-001",
        "WorkOrderId": 200001,
        "ItemNumber": "FG-WIDGET-100",
        "PlannedQuantity": 100,
        "PlannedStartDate": "2026-03-22T06:00:00Z",
        "PlannedCompletionDate": "2026-03-22T18:00:00Z",
        "WorkOrderPriority": "3",
        "UOMCode": "EA",
        "StructureName": "PRIMARY",
        "RoutingName": "RTG-WIDGET-100",
        "OrganizationCode": "ORG_MAIN",
        "WorkOrderType": "Standard",
        "WorkOrderStatusCode": "Released",
    },
    {
        "WorkOrderNumber": "WO-100-002",
        "WorkOrderId": 200002,
        "ItemNumber": "FG-WIDGET-100",
        "PlannedQuantity": 250,
        "PlannedStartDate": "2026-03-23T06:00:00Z",
        "PlannedCompletionDate": "2026-03-24T06:00:00Z",
        "WorkOrderPriority": "2",
        "UOMCode": "EA",
        "StructureName": "PRIMARY",
        "RoutingName": "RTG-WIDGET-100",
        "OrganizationCode": "ORG_MAIN",
        "WorkOrderType": "Standard",
        "WorkOrderStatusCode": "Released",
    },
    {
        "WorkOrderNumber": "WO-200-001",
        "WorkOrderId": 200003,
        "ItemNumber": "FG-WIDGET-200",
        "PlannedQuantity": 50,
        "PlannedStartDate": "2026-03-22T08:00:00Z",
        "PlannedCompletionDate": "2026-03-23T08:00:00Z",
        "WorkOrderPriority": "1",
        "UOMCode": "EA",
        "StructureName": "PRIMARY",
        "RoutingName": "RTG-WIDGET-200",
        "OrganizationCode": "ORG_MAIN",
        "WorkOrderType": "Standard",
        "WorkOrderStatusCode": "Released",
    },
    {
        "WorkOrderNumber": "WO-300-001",
        "WorkOrderId": 200004,
        "ItemNumber": "FG-GADGET-300",
        "PlannedQuantity": 200,
        "PlannedStartDate": "2026-03-24T06:00:00Z",
        "PlannedCompletionDate": "2026-03-26T18:00:00Z",
        "WorkOrderPriority": "2",
        "UOMCode": "EA",
        "StructureName": "PRIMARY",
        "RoutingName": "RTG-GADGET-300",
        "OrganizationCode": "ORG_MAIN",
        "WorkOrderType": "Standard",
        "WorkOrderStatusCode": "Unreleased",
    },
    {
        "WorkOrderNumber": "WO-300-002",
        "WorkOrderId": 200005,
        "ItemNumber": "FG-GADGET-300",
        "PlannedQuantity": 75,
        "PlannedStartDate": "2026-03-27T06:00:00Z",
        "PlannedCompletionDate": "2026-03-28T18:00:00Z",
        "WorkOrderPriority": "4",
        "UOMCode": "EA",
        "StructureName": "PRIMARY",
        "RoutingName": "RTG-GADGET-300",
        "OrganizationCode": "ORG_MAIN",
        "WorkOrderType": "Standard",
        "WorkOrderStatusCode": "Released",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Routings  (Oracle Manufacturing Work Definition Operations)
#
# Keyed by product code.  Each routing contains ``Operation`` list.
# ═══════════════════════════════════════════════════════════════════

ORACLE_ROUTINGS: dict[str, list[dict]] = {
    "FG-WIDGET-100": [
        {
            "ItemNumber": "FG-WIDGET-100",
            "RoutingName": "RTG-WIDGET-100",
            "AlternateRoutingDesignator": "1",
            "OrganizationCode": "ORG_MAIN",
            "Operation": [
                {
                    "OperationSequenceNumber": "10",
                    "OperationName": "Cut and form steel housing",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-CUT-01",
                    "OperationDescription": "Cut and form steel housing",
                },
                {
                    "OperationSequenceNumber": "20",
                    "OperationName": "SMT assembly — control PCB",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-SMT-01",
                    "OperationDescription": "SMT assembly — control PCB",
                },
                {
                    "OperationSequenceNumber": "30",
                    "OperationName": "Final assembly — housing + PCB",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-ASSY-01",
                    "OperationDescription": "Final assembly — housing + PCB",
                },
                {
                    "OperationSequenceNumber": "40",
                    "OperationName": "Functional test",
                    "OperationType": "Inspection",
                    "WorkCenterName": "WC-TEST-01",
                    "OperationDescription": "Functional test",
                },
                {
                    "OperationSequenceNumber": "50",
                    "OperationName": "Labelling and packaging",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-PACK-01",
                    "OperationDescription": "Labelling and packaging",
                },
            ],
        },
    ],
    "FG-WIDGET-200": [
        {
            "ItemNumber": "FG-WIDGET-200",
            "RoutingName": "RTG-WIDGET-200",
            "AlternateRoutingDesignator": "1",
            "OrganizationCode": "ORG_MAIN",
            "Operation": [
                {
                    "OperationSequenceNumber": "10",
                    "OperationName": "CNC machine aluminium housing",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-CNC-01",
                    "OperationDescription": "CNC machine aluminium housing",
                },
                {
                    "OperationSequenceNumber": "20",
                    "OperationName": "Anodize housing",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-FINISH-01",
                    "OperationDescription": "Anodize housing",
                },
                {
                    "OperationSequenceNumber": "30",
                    "OperationName": "SMT assembly — control PCB",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-SMT-01",
                    "OperationDescription": "SMT assembly — control PCB",
                },
                {
                    "OperationSequenceNumber": "40",
                    "OperationName": "Install display module",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-ASSY-01",
                    "OperationDescription": "Install display module",
                },
                {
                    "OperationSequenceNumber": "50",
                    "OperationName": "Final assembly — housing + PCB + display",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-ASSY-01",
                    "OperationDescription": "Final assembly — housing + PCB + display",
                },
                {
                    "OperationSequenceNumber": "60",
                    "OperationName": "Functional test and calibration",
                    "OperationType": "Inspection",
                    "WorkCenterName": "WC-TEST-01",
                    "OperationDescription": "Functional test and calibration",
                },
                {
                    "OperationSequenceNumber": "70",
                    "OperationName": "Labelling and premium packaging",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-PACK-01",
                    "OperationDescription": "Labelling and premium packaging",
                },
            ],
        },
    ],
    "FG-GADGET-300": [
        {
            "ItemNumber": "FG-GADGET-300",
            "RoutingName": "RTG-GADGET-300",
            "AlternateRoutingDesignator": "1",
            "OrganizationCode": "ORG_MAIN",
            "Operation": [
                {
                    "OperationSequenceNumber": "10",
                    "OperationName": "Injection mould ABS case",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-MOULD-01",
                    "OperationDescription": "Injection mould ABS case",
                },
                {
                    "OperationSequenceNumber": "20",
                    "OperationName": "SMT assembly — control PCB",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-SMT-01",
                    "OperationDescription": "SMT assembly — control PCB",
                },
                {
                    "OperationSequenceNumber": "30",
                    "OperationName": "Sensor + battery sub-assembly",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-ASSY-02",
                    "OperationDescription": "Sensor + battery sub-assembly",
                },
                {
                    "OperationSequenceNumber": "40",
                    "OperationName": "Final assembly — case + internals",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-ASSY-01",
                    "OperationDescription": "Final assembly — case + internals",
                },
                {
                    "OperationSequenceNumber": "50",
                    "OperationName": "Burn-in and functional test",
                    "OperationType": "Inspection",
                    "WorkCenterName": "WC-TEST-02",
                    "OperationDescription": "Burn-in and functional test",
                },
                {
                    "OperationSequenceNumber": "60",
                    "OperationName": "Labelling and packaging",
                    "OperationType": "Production",
                    "WorkCenterName": "WC-PACK-01",
                    "OperationDescription": "Labelling and packaging",
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Work Centers  (Oracle Manufacturing Resources / Work Centers)
# ═══════════════════════════════════════════════════════════════════

ORACLE_WORK_CENTERS: list[dict] = [
    {
        "WorkCenterName": "WC-CUT-01",
        "Description": "Cutting Station 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Machine",
        "ResourceCount": "8",
    },
    {
        "WorkCenterName": "WC-CNC-01",
        "Description": "CNC Machining Centre 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Machine",
        "ResourceCount": "4",
    },
    {
        "WorkCenterName": "WC-FINISH-01",
        "Description": "Surface Finishing / Anodizing",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Process",
        "ResourceCount": "12",
    },
    {
        "WorkCenterName": "WC-MOULD-01",
        "Description": "Injection Moulding Cell 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Machine",
        "ResourceCount": "6",
    },
    {
        "WorkCenterName": "WC-SMT-01",
        "Description": "SMT Pick-and-Place Line 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Line",
        "ResourceCount": "2",
    },
    {
        "WorkCenterName": "WC-ASSY-01",
        "Description": "Manual Assembly Station 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Labor",
        "ResourceCount": "10",
    },
    {
        "WorkCenterName": "WC-ASSY-02",
        "Description": "Manual Assembly Station 02",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Labor",
        "ResourceCount": "10",
    },
    {
        "WorkCenterName": "WC-TEST-01",
        "Description": "Functional Test Bench 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Machine",
        "ResourceCount": "6",
    },
    {
        "WorkCenterName": "WC-TEST-02",
        "Description": "Burn-in / Environmental Test 02",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Machine",
        "ResourceCount": "4",
    },
    {
        "WorkCenterName": "WC-PACK-01",
        "Description": "Packaging Station 01",
        "OrganizationCode": "ORG_MAIN",
        "WorkCenterType": "Labor",
        "ResourceCount": "8",
    },
]
