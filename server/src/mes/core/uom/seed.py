"""
UOM: Built-in seed data for out-of-the-box units of measure.

SI fundamentals:  kg, s, m, K
Additional SI:    g; min, h, d; km; °C; L, m³
US imperial:      lb, oz; ft; °F; fl_oz
Rate:             EA/h, EA/min, kg/h, L/h, PC/h

The conversion model uses an affine formula relative to each type's base unit:
    base_value = value * multiplier + offset

Temperature examples:
    °C → K : K = C * 1.0 + 273.15
    °F → K : K = F * (5/9) + 255.372222…

Rate UoMs are composite: numerator UoM / denominator UoM.
Conversion between rate UoMs independently converts each component.
"""

from __future__ import annotations

from uuid import UUID

# Each entry: (symbol, name, uom_type, multiplier, offset)
BUILTIN_UNITS: list[tuple[str, str, str, float, float]] = [
    # ── SI FUNDAMENTAL ──────────────────────────────────────────────
    ("kg",  "kilogram",          "mass",        1.0,             0.0),
    ("s",   "second",            "time",        1.0,             0.0),
    ("m",   "meter",             "length",      1.0,             0.0),
    ("K",   "kelvin",            "temperature", 1.0,             0.0),

    # ── SI DERIVED / ADDITIONAL ─────────────────────────────────────
    # Mass
    ("g",   "gram",              "mass",        0.001,           0.0),
    # Time
    ("min", "minute",            "time",        60.0,            0.0),
    ("h",   "hour",              "time",        3600.0,          0.0),
    ("d",   "day",               "time",        86400.0,         0.0),
    # Length
    ("km",  "kilometer",         "length",      1000.0,          0.0),
    # Temperature
    ("°C",  "degree Celsius",    "temperature", 1.0,             273.15),
    # Volume  (base unit = m³)
    ("m³",  "cubic meter",       "volume",      1.0,             0.0),
    ("L",   "liter",             "volume",      0.001,           0.0),

    # ── US IMPERIAL ─────────────────────────────────────────────────
    # Mass
    ("lb",  "pound",             "mass",        0.45359237,      0.0),
    ("oz",  "ounce",             "mass",        0.028349523125,  0.0),
    # Length
    ("ft",  "foot",              "length",      0.3048,          0.0),
    # Temperature  ( K = F × 5/9 + 255.3722… )
    ("°F",  "degree Fahrenheit", "temperature", 5.0 / 9.0,      273.15 - 32.0 * 5.0 / 9.0),
    # Volume
    ("fl_oz", "fluid ounce",    "volume",      2.95735295625e-5, 0.0),

    # ── COUNT / DISCRETE ────────────────────────────────────────────
    ("EA",  "each",              "count",       1.0,             0.0),
    ("PC",  "piece",             "count",       1.0,             0.0),
]

# Each entry: (symbol, name, numerator_symbol, denominator_symbol)
BUILTIN_RATE_UNITS: list[tuple[str, str, str, str]] = [
    ("EA/h",   "each per hour",      "EA", "h"),
    ("EA/min", "each per minute",    "EA", "min"),
    ("kg/h",   "kilograms per hour", "kg", "h"),
    ("L/h",    "liters per hour",    "L",  "h"),
    ("PC/h",   "pieces per hour",    "PC", "h"),
]


def get_builtin_unit_dicts() -> list[dict]:
    """
    Return the built-in units as a list of dicts ready for
    ``UnitOfMeasure(**d)`` construction.
    """
    return [
        {
            "symbol": symbol,
            "name": name,
            "uom_type": uom_type,
            "multiplier": multiplier,
            "offset": offset,
            "is_builtin": True,
        }
        for symbol, name, uom_type, multiplier, offset in BUILTIN_UNITS
    ]


def get_builtin_rate_unit_dicts(symbol_to_id: dict[str, UUID]) -> list[dict]:
    """
    Return the built-in rate units as a list of dicts.

    *symbol_to_id* must map base-unit symbols to their database UUIDs
    (populated after base units are flushed).
    """
    return [
        {
            "symbol": symbol,
            "name": name,
            "uom_type": "rate",
            "multiplier": 1.0,
            "offset": 0.0,
            "numerator_uom_id": symbol_to_id[num_sym],
            "denominator_uom_id": symbol_to_id[den_sym],
            "is_builtin": True,
        }
        for symbol, name, num_sym, den_sym in BUILTIN_RATE_UNITS
    ]
