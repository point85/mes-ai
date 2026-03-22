"""
SAP ERP Simulator: realistic SAP OData V4 fixture data.

Every record uses genuine SAP field names as they appear in the S/4HANA
OData V4 APIs.  The SAPS4HANATransformLayer in
``mes.adapters.erp.sap_s4hana.transform`` maps these into MES canonical DTOs.

Organisational hierarchy
~~~~~~~~~~~~~~~~~~~~~~~~
- Company Code (Buchungskreis): 1000 — "Global Manufacturing Co."
- Plant (Werk): 1000 — "Main Plant"
- Storage Location (Lagerort): 0001 — "Main Warehouse"

Product catalogue
~~~~~~~~~~~~~~~~~
Three finished goods (FERT), each with a BOM and routing:
  FG-WIDGET-100  — Standard Widget (steel housing + PCB + screws)
  FG-WIDGET-200  — Premium Widget (aluminium housing + PCB + display + screws)
  FG-GADGET-300  — Gadget Model X (plastic case + PCB + battery + sensor)

Raw / semi-finished materials feed into those BOMs.
"""

from __future__ import annotations

from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════
# Materials  (SAP transaction MM01 — /API_MATERIAL_SRV)
# ═══════════════════════════════════════════════════════════════════

SAP_MATERIALS: list[dict] = [
    # ── Raw materials (ROH) ──────────────────────────────────────
    {
        "Material": "RM-STEEL-1MM",
        "MaterialName": "Carbon Steel Sheet 1 mm",
        "MaterialType": "ROH",
        "BaseUnit": "KG",
        "MaterialDescription": "Cold-rolled carbon steel sheet, 1 mm thickness",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "001",
        "Plant": "1000",
    },
    {
        "Material": "RM-ALUM-2MM",
        "MaterialName": "Aluminium Sheet 2 mm",
        "MaterialType": "ROH",
        "BaseUnit": "KG",
        "MaterialDescription": "6061-T6 aluminium alloy sheet, 2 mm thickness",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "001",
        "Plant": "1000",
    },
    {
        "Material": "RM-ABS-PELLET",
        "MaterialName": "ABS Plastic Pellets",
        "MaterialType": "ROH",
        "BaseUnit": "KG",
        "MaterialDescription": "Injection-grade ABS resin pellets",
        "MaximumStoragePeriod": "730",
        "MaterialGroup": "002",
        "Plant": "1000",
    },
    {
        "Material": "RM-SCREW-M3",
        "MaterialName": "M3x10 Machine Screw SS",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "M3 x 10 mm stainless steel pan-head machine screw",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "003",
        "Plant": "1000",
    },
    {
        "Material": "RM-SCREW-M4",
        "MaterialName": "M4x12 Machine Screw SS",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "M4 x 12 mm stainless steel pan-head machine screw",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "003",
        "Plant": "1000",
    },
    {
        "Material": "RM-COPPER-WIRE",
        "MaterialName": "Copper Wire 0.5 mm",
        "MaterialType": "ROH",
        "BaseUnit": "M",
        "MaterialDescription": "Enamelled copper magnet wire, 0.5 mm diameter",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "004",
        "Plant": "1000",
    },
    {
        "Material": "RM-RESISTOR-10K",
        "MaterialName": "Resistor 10 kΩ 0805",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "SMD resistor 10 kΩ ±1 %, 0805 package",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "005",
        "Plant": "1000",
    },
    {
        "Material": "RM-CAP-100UF",
        "MaterialName": "Capacitor 100 µF 25 V",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "Electrolytic capacitor 100 µF 25 V",
        "MaximumStoragePeriod": "1825",
        "MaterialGroup": "005",
        "Plant": "1000",
    },
    {
        "Material": "RM-DISPLAY-OLED",
        "MaterialName": "OLED Display Module 1.3 in",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "128×64 OLED display module, I2C interface",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "006",
        "Plant": "1000",
    },
    {
        "Material": "RM-BATTERY-LIPO",
        "MaterialName": "LiPo Battery 3.7 V 2000 mAh",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "Lithium polymer rechargeable battery, 3.7 V / 2000 mAh",
        "MaximumStoragePeriod": "365",
        "MaterialGroup": "007",
        "Plant": "1000",
    },
    {
        "Material": "RM-SENSOR-TEMP",
        "MaterialName": "Temperature Sensor NTC 10 kΩ",
        "MaterialType": "ROH",
        "BaseUnit": "EA",
        "MaterialDescription": "NTC thermistor 10 kΩ ±1 %, waterproof probe",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "005",
        "Plant": "1000",
    },
    {
        "Material": "RM-LABEL-PROD",
        "MaterialName": "Product Label 50×30 mm",
        "MaterialType": "VERP",
        "BaseUnit": "EA",
        "MaterialDescription": "Self-adhesive product identification label",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "008",
        "Plant": "1000",
    },
    {
        "Material": "RM-BOX-SM",
        "MaterialName": "Corrugated Box Small",
        "MaterialType": "VERP",
        "BaseUnit": "EA",
        "MaterialDescription": "Single-wall corrugated shipping box 200×150×100 mm",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "008",
        "Plant": "1000",
    },

    # ── Semi-finished materials (HALB) ───────────────────────────
    {
        "Material": "SF-PCB-CTRL",
        "MaterialName": "Main Control PCB Assembly",
        "MaterialType": "HALB",
        "BaseUnit": "EA",
        "MaterialDescription": "Assembled and tested main control board",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "010",
        "Plant": "1000",
    },
    {
        "Material": "SF-HOUSING-STEEL",
        "MaterialName": "Steel Housing Formed",
        "MaterialType": "HALB",
        "BaseUnit": "EA",
        "MaterialDescription": "Stamped and bent carbon steel housing",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "011",
        "Plant": "1000",
    },
    {
        "Material": "SF-HOUSING-ALUM",
        "MaterialName": "Aluminium Housing CNC",
        "MaterialType": "HALB",
        "BaseUnit": "EA",
        "MaterialDescription": "CNC-machined aluminium housing with anodized finish",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "011",
        "Plant": "1000",
    },
    {
        "Material": "SF-CASE-ABS",
        "MaterialName": "ABS Plastic Case",
        "MaterialType": "HALB",
        "BaseUnit": "EA",
        "MaterialDescription": "Injection-moulded ABS case (top + bottom)",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "011",
        "Plant": "1000",
    },

    # ── Finished goods (FERT) ────────────────────────────────────
    {
        "Material": "FG-WIDGET-100",
        "MaterialName": "Standard Widget 100",
        "MaterialType": "FERT",
        "BaseUnit": "EA",
        "MaterialDescription": "Standard widget w/ steel housing and control PCB",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "020",
        "Plant": "1000",
    },
    {
        "Material": "FG-WIDGET-200",
        "MaterialName": "Premium Widget 200",
        "MaterialType": "FERT",
        "BaseUnit": "EA",
        "MaterialDescription": "Premium widget w/ aluminium housing, display, and control PCB",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "020",
        "Plant": "1000",
    },
    {
        "Material": "FG-GADGET-300",
        "MaterialName": "Gadget Model 300",
        "MaterialType": "FERT",
        "BaseUnit": "EA",
        "MaterialDescription": "Portable gadget w/ ABS case, battery, sensor, and PCB",
        "MaximumStoragePeriod": None,
        "MaterialGroup": "021",
        "Plant": "1000",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Products  (SAP /API_PRODUCT_SRV — finished goods only)
# ═══════════════════════════════════════════════════════════════════

SAP_PRODUCTS: list[dict] = [
    {
        "Product": "FG-WIDGET-100",
        "ProductDescription": "Standard Widget 100",
        "MaterialType": "FERT",
        "MaterialRevisionLevel": "1.0",
        "IndustrySector": "M",
    },
    {
        "Product": "FG-WIDGET-200",
        "ProductDescription": "Premium Widget 200",
        "MaterialType": "FERT",
        "MaterialRevisionLevel": "1.0",
        "IndustrySector": "M",
    },
    {
        "Product": "FG-GADGET-300",
        "ProductDescription": "Gadget Model 300",
        "MaterialType": "FERT",
        "MaterialRevisionLevel": "2.0",
        "IndustrySector": "M",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Bills of Material  (SAP transaction CS01 — /API_BILL_OF_MATERIAL_SRV)
#
# Keyed by product code for lookup in sync_boms(product_id).
# Each record includes SAP OData V4 navigation property ``to_BOMItem``.
# ═══════════════════════════════════════════════════════════════════

SAP_BOMS: dict[str, list[dict]] = {
    "FG-WIDGET-100": [
        {
            "Material": "FG-WIDGET-100",
            "BillOfMaterial": "00001001",
            "BillOfMaterialVariant": "01",
            "BillOfMaterialVariantUsage": "1",
            "to_BOMItem": [
                {
                    "BillOfMaterialItemNumber": "0010",
                    "BillOfMaterialComponent": "SF-HOUSING-STEEL",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0020",
                    "BillOfMaterialComponent": "SF-PCB-CTRL",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0030",
                    "BillOfMaterialComponent": "RM-SCREW-M3",
                    "BillOfMaterialItemQuantity": "6",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0040",
                    "BillOfMaterialComponent": "RM-LABEL-PROD",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
            ],
        },
    ],
    "FG-WIDGET-200": [
        {
            "Material": "FG-WIDGET-200",
            "BillOfMaterial": "00001002",
            "BillOfMaterialVariant": "01",
            "BillOfMaterialVariantUsage": "1",
            "to_BOMItem": [
                {
                    "BillOfMaterialItemNumber": "0010",
                    "BillOfMaterialComponent": "SF-HOUSING-ALUM",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0020",
                    "BillOfMaterialComponent": "SF-PCB-CTRL",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0030",
                    "BillOfMaterialComponent": "RM-DISPLAY-OLED",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0040",
                    "BillOfMaterialComponent": "RM-SCREW-M4",
                    "BillOfMaterialItemQuantity": "8",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0050",
                    "BillOfMaterialComponent": "RM-LABEL-PROD",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
            ],
        },
    ],
    "FG-GADGET-300": [
        {
            "Material": "FG-GADGET-300",
            "BillOfMaterial": "00001003",
            "BillOfMaterialVariant": "01",
            "BillOfMaterialVariantUsage": "1",
            "to_BOMItem": [
                {
                    "BillOfMaterialItemNumber": "0010",
                    "BillOfMaterialComponent": "SF-CASE-ABS",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0020",
                    "BillOfMaterialComponent": "SF-PCB-CTRL",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0030",
                    "BillOfMaterialComponent": "RM-BATTERY-LIPO",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0040",
                    "BillOfMaterialComponent": "RM-SENSOR-TEMP",
                    "BillOfMaterialItemQuantity": "2",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0050",
                    "BillOfMaterialComponent": "RM-SCREW-M3",
                    "BillOfMaterialItemQuantity": "4",
                    "BillOfMaterialItemUnit": "EA",
                },
                {
                    "BillOfMaterialItemNumber": "0060",
                    "BillOfMaterialComponent": "RM-LABEL-PROD",
                    "BillOfMaterialItemQuantity": "1",
                    "BillOfMaterialItemUnit": "EA",
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Production Orders  (SAP transaction CO01 — /API_PRODUCTION_ORDER_2_SRV)
# ═══════════════════════════════════════════════════════════════════

SAP_PRODUCTION_ORDERS: list[dict] = [
    {
        "ManufacturingOrder": "000001000100",
        "Material": "FG-WIDGET-100",
        "TotalQuantity": "100",
        "MfgOrderPlannedStartDate": "2026-03-22T06:00:00Z",
        "MfgOrderPlannedEndDate": "2026-03-22T18:00:00Z",
        "MfgOrderPriority": "3",
        "ProductionUnit": "EA",
        "BillOfMaterial": "00001001",
        "ProductionRouting": "50000001",
        "ProductionPlant": "1000",
        "ManufacturingOrderType": "PP01",
        "MfgOrderStatus": "REL",
        "MRPController": "001",
    },
    {
        "ManufacturingOrder": "000001000101",
        "Material": "FG-WIDGET-100",
        "TotalQuantity": "250",
        "MfgOrderPlannedStartDate": "2026-03-23T06:00:00Z",
        "MfgOrderPlannedEndDate": "2026-03-24T06:00:00Z",
        "MfgOrderPriority": "2",
        "ProductionUnit": "EA",
        "BillOfMaterial": "00001001",
        "ProductionRouting": "50000001",
        "ProductionPlant": "1000",
        "ManufacturingOrderType": "PP01",
        "MfgOrderStatus": "REL",
        "MRPController": "001",
    },
    {
        "ManufacturingOrder": "000001000200",
        "Material": "FG-WIDGET-200",
        "TotalQuantity": "50",
        "MfgOrderPlannedStartDate": "2026-03-22T08:00:00Z",
        "MfgOrderPlannedEndDate": "2026-03-23T08:00:00Z",
        "MfgOrderPriority": "1",
        "ProductionUnit": "EA",
        "BillOfMaterial": "00001002",
        "ProductionRouting": "50000002",
        "ProductionPlant": "1000",
        "ManufacturingOrderType": "PP01",
        "MfgOrderStatus": "REL",
        "MRPController": "001",
    },
    {
        "ManufacturingOrder": "000001000300",
        "Material": "FG-GADGET-300",
        "TotalQuantity": "200",
        "MfgOrderPlannedStartDate": "2026-03-24T06:00:00Z",
        "MfgOrderPlannedEndDate": "2026-03-26T18:00:00Z",
        "MfgOrderPriority": "2",
        "ProductionUnit": "EA",
        "BillOfMaterial": "00001003",
        "ProductionRouting": "50000003",
        "ProductionPlant": "1000",
        "ManufacturingOrderType": "PP01",
        "MfgOrderStatus": "CRTD",
        "MRPController": "002",
    },
    {
        "ManufacturingOrder": "000001000301",
        "Material": "FG-GADGET-300",
        "TotalQuantity": "75",
        "MfgOrderPlannedStartDate": "2026-03-27T06:00:00Z",
        "MfgOrderPlannedEndDate": "2026-03-28T18:00:00Z",
        "MfgOrderPriority": "4",
        "ProductionUnit": "EA",
        "BillOfMaterial": "00001003",
        "ProductionRouting": "50000003",
        "ProductionPlant": "1000",
        "ManufacturingOrderType": "PP01",
        "MfgOrderStatus": "REL",
        "MRPController": "002",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Process Routings  (SAP transaction CA01 — /API_PRODUCTION_ROUTING)
#
# Keyed by product code. Each routing contains ``to_Operation``.
# ═══════════════════════════════════════════════════════════════════

SAP_ROUTINGS: dict[str, list[dict]] = {
    "FG-WIDGET-100": [
        {
            "Material": "FG-WIDGET-100",
            "ProductionRoutingGroup": "50000001",
            "ProductionRoutingGroupCounter": "01",
            "Plant": "1000",
            "to_Operation": [
                {
                    "OperationNumber": "0010",
                    "OperationText": "Cut and form steel housing",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-CUT-01",
                },
                {
                    "OperationNumber": "0020",
                    "OperationText": "SMT assembly — control PCB",
                    "OperationControlProfile": "PP02",
                    "WorkCenter": "WC-SMT-01",
                },
                {
                    "OperationNumber": "0030",
                    "OperationText": "Final assembly — housing + PCB",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-ASSY-01",
                },
                {
                    "OperationNumber": "0040",
                    "OperationText": "Functional test",
                    "OperationControlProfile": "QM01",
                    "WorkCenter": "WC-TEST-01",
                },
                {
                    "OperationNumber": "0050",
                    "OperationText": "Labelling and packaging",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-PACK-01",
                },
            ],
        },
    ],
    "FG-WIDGET-200": [
        {
            "Material": "FG-WIDGET-200",
            "ProductionRoutingGroup": "50000002",
            "ProductionRoutingGroupCounter": "01",
            "Plant": "1000",
            "to_Operation": [
                {
                    "OperationNumber": "0010",
                    "OperationText": "CNC machine aluminium housing",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-CNC-01",
                },
                {
                    "OperationNumber": "0020",
                    "OperationText": "Anodize housing",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-FINISH-01",
                },
                {
                    "OperationNumber": "0030",
                    "OperationText": "SMT assembly — control PCB",
                    "OperationControlProfile": "PP02",
                    "WorkCenter": "WC-SMT-01",
                },
                {
                    "OperationNumber": "0040",
                    "OperationText": "Install display module",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-ASSY-01",
                },
                {
                    "OperationNumber": "0050",
                    "OperationText": "Final assembly — housing + PCB + display",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-ASSY-01",
                },
                {
                    "OperationNumber": "0060",
                    "OperationText": "Functional test and calibration",
                    "OperationControlProfile": "QM01",
                    "WorkCenter": "WC-TEST-01",
                },
                {
                    "OperationNumber": "0070",
                    "OperationText": "Labelling and premium packaging",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-PACK-01",
                },
            ],
        },
    ],
    "FG-GADGET-300": [
        {
            "Material": "FG-GADGET-300",
            "ProductionRoutingGroup": "50000003",
            "ProductionRoutingGroupCounter": "01",
            "Plant": "1000",
            "to_Operation": [
                {
                    "OperationNumber": "0010",
                    "OperationText": "Injection mould ABS case",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-MOULD-01",
                },
                {
                    "OperationNumber": "0020",
                    "OperationText": "SMT assembly — control PCB",
                    "OperationControlProfile": "PP02",
                    "WorkCenter": "WC-SMT-01",
                },
                {
                    "OperationNumber": "0030",
                    "OperationText": "Sensor + battery sub-assembly",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-ASSY-02",
                },
                {
                    "OperationNumber": "0040",
                    "OperationText": "Final assembly — case + internals",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-ASSY-01",
                },
                {
                    "OperationNumber": "0050",
                    "OperationText": "Burn-in and functional test",
                    "OperationControlProfile": "QM01",
                    "WorkCenter": "WC-TEST-02",
                },
                {
                    "OperationNumber": "0060",
                    "OperationText": "Labelling and packaging",
                    "OperationControlProfile": "PP01",
                    "WorkCenter": "WC-PACK-01",
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Work Centers  (SAP transaction CR01 — /API_WORK_CENTERS)
# ═══════════════════════════════════════════════════════════════════

SAP_WORK_CENTERS: list[dict] = [
    {
        "WorkCenter": "WC-CUT-01",
        "WorkCenterText": "Cutting Station 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0001",
        "Capacity": "8",
    },
    {
        "WorkCenter": "WC-CNC-01",
        "WorkCenterText": "CNC Machining Centre 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0001",
        "Capacity": "4",
    },
    {
        "WorkCenter": "WC-FINISH-01",
        "WorkCenterText": "Surface Finishing / Anodizing",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0002",
        "Capacity": "12",
    },
    {
        "WorkCenter": "WC-MOULD-01",
        "WorkCenterText": "Injection Moulding Cell 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0001",
        "Capacity": "6",
    },
    {
        "WorkCenter": "WC-SMT-01",
        "WorkCenterText": "SMT Pick-and-Place Line 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0003",
        "Capacity": "2",
    },
    {
        "WorkCenter": "WC-ASSY-01",
        "WorkCenterText": "Manual Assembly Station 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0004",
        "Capacity": "10",
    },
    {
        "WorkCenter": "WC-ASSY-02",
        "WorkCenterText": "Manual Assembly Station 02",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0004",
        "Capacity": "10",
    },
    {
        "WorkCenter": "WC-TEST-01",
        "WorkCenterText": "Functional Test Bench 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0005",
        "Capacity": "6",
    },
    {
        "WorkCenter": "WC-TEST-02",
        "WorkCenterText": "Burn-in / Environmental Test 02",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0005",
        "Capacity": "4",
    },
    {
        "WorkCenter": "WC-PACK-01",
        "WorkCenterText": "Packaging Station 01",
        "Plant": "1000",
        "WorkCenterCategoryCode": "0006",
        "Capacity": "15",
    },
]
