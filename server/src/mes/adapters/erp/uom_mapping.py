"""
ERP UOM Normalization: Maps ERP-specific unit codes to MES UOM symbols.

Each ERP system may use different codes for the same unit (e.g. SAP uses "KG",
Oracle uses "Kg", MES stores "kg"). This module provides a shared mapping so
that all ERP transforms resolve to consistent MES UOM symbols.

Usage:
    from mes.adapters.erp.uom_mapping import normalize_erp_uom
    mes_uom = normalize_erp_uom("KG")  # -> "kg"
"""

from __future__ import annotations

# Canonical mapping: uppercase ERP code -> MES UOM symbol.
# Covers SAP, Oracle Cloud, and common ERP UOM codes.
_ERP_TO_MES_UOM: dict[str, str] = {
    # Mass
    "KG": "kg",
    "G": "g",
    "LB": "lb",
    "OZ": "oz",
    # Length
    "M": "m",
    "KM": "km",
    "FT": "ft",
    # Volume
    "L": "L",
    "M3": "m³",
    "FL_OZ": "fl_oz",
    # Time
    "S": "s",
    "MIN": "min",
    "H": "h",
    "D": "d",
    # Count / piece (pass-through)
    "EA": "EA",
    "PC": "PC",
    # Temperature
    "CEL": "°C",
    "FAH": "°F",
    "K": "K",
}


def normalize_erp_uom(erp_uom: str) -> str:
    """
    Normalize an ERP unit-of-measure code to the MES UOM symbol.

    Lookup is case-insensitive. If no mapping is found, returns the
    original code unchanged (allows user-defined UOMs to pass through).
    """
    return _ERP_TO_MES_UOM.get(erp_uom.upper(), erp_uom)
