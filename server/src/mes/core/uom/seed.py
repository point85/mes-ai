"""
UOM: Built-in seed data for out-of-the-box units of measure.

Nine types (eight SI base quantities + count):
    mass                — base: kg
    length              — base: m
    time                — base: s
    temperature         — base: K
    electrical          — base: A
    force               — base: N
    amount_of_substance — base: mol
    luminous_intensity  — base: cd
    count               — base: EA (each)

Four classes:
    scalar    — single unit with affine conversion
    quotient  — left / right   (e.g. kg/s)
    product   — left × right   (e.g. m² via product … see power)
    power     — left ^ exponent (e.g. m³)

Affine formula:   base_value = value * multiplier + offset
Temperature:
    °C → K : K = C * 1.0 + 273.15
    °F → K : K = F * (5/9) + 255.3722…
"""

from __future__ import annotations

from uuid import UUID

# ── Scalar units ────────────────────────────────────────────────────
# (symbol, name, uom_type, multiplier, offset)
BUILTIN_SCALARS: list[tuple[str, str, str, float, float]] = [
    # ── SI FUNDAMENTALS (base units, multiplier=1, offset=0) ────────
    ("kg",     "kilogram",            "mass",                  1.0,                0.0),
    ("s",      "second",              "time",                  1.0,                0.0),
    ("m",      "meter",               "length",                1.0,                0.0),
    ("K",      "kelvin",              "temperature",           1.0,                0.0),
    ("A",      "ampere",              "electrical",            1.0,                0.0),
    ("mol",    "mole",                "amount_of_substance",   1.0,                0.0),
    ("cd",     "candela",             "luminous_intensity",    1.0,                0.0),
    ("EA",     "each",                "count",                 1.0,                0.0),

    # ── MASS ─────────────────────────────────────────────────────────
    ("mg",     "milligram",           "mass",        1.0e-6,                       0.0),
    ("g",      "gram",                "mass",        0.001,                        0.0),
    ("t",      "metric ton",          "mass",        1000.0,                       0.0),
    ("lb",     "pound",               "mass",        0.45359237,                   0.0),
    ("oz",     "ounce",               "mass",        0.028349523125,               0.0),

    # ── TIME ─────────────────────────────────────────────────────────
    ("min",    "minute",              "time",        60.0,                         0.0),
    ("h",      "hour",                "time",        3600.0,                       0.0),
    ("d",      "day",                 "time",        86400.0,                      0.0),
    ("wk",     "week",                "time",        604800.0,                     0.0),

    # ── LENGTH ───────────────────────────────────────────────────────
    ("mm",     "millimeter",          "length",      0.001,                        0.0),
    ("cm",     "centimeter",          "length",      0.01,                         0.0),
    ("km",     "kilometer",           "length",      1000.0,                       0.0),
    ("in",     "inch",                "length",      0.0254,                       0.0),
    ("ft",     "foot",                "length",      0.3048,                       0.0),
    ("yd",     "yard",                "length",      0.9144,                       0.0),

    # ── VOLUME (treated as length type: multiplier = m³ equivalent) ──
    ("L",      "liter",               "length",      0.001,                        0.0),
    ("mL",     "milliliter",          "length",      1.0e-6,                       0.0),
    ("fl oz",  "fluid ounce",         "length",      2.957352965e-5,               0.0),

    # ── TEMPERATURE ──────────────────────────────────────────────────
    ("°C",     "degree Celsius",      "temperature", 1.0,                          273.15),
    ("°F",     "degree Fahrenheit",   "temperature", 5.0 / 9.0,                   273.15 - 32.0 * 5.0 / 9.0),

    # ── LENGTH (misc) ────────────────────────────────────────────────
    ("µm",     "micrometer",          "length",      1.0e-6,                       0.0),

    # ── ELECTRICAL ───────────────────────────────────────────────────
    ("mA",     "milliampere",         "electrical",  0.001,                        0.0),
    ("V",      "volt",                "electrical",  1.0,                          0.0),

    # ── FORCE / PRESSURE / TORQUE ────────────────────────────────────
    ("N",      "newton",              "force",       1.0,                          0.0),
    ("Pa",     "pascal",              "force",       1.0,                          0.0),
    ("kPa",    "kilopascal",          "force",       1000.0,                       0.0),
    ("Nm",     "newton-meter",        "force",       1.0,                          0.0),

    # ── PROCESS / BIOLOGICAL ─────────────────────────────────────────
    ("°Bx",    "degrees Brix",        "mass",        1.0,                          0.0),
    ("pH",     "pH",                  "amount_of_substance", 1.0,                 0.0),
    ("CFU/mL", "colony-forming units per mL", "count", 1.0,                       0.0),

    # ── COUNT (discrete / count / rates) ─────────────────────────────
    ("PC",     "piece",               "count",       1.0,                          0.0),
    ("can",    "can",                 "count",       1.0,                          0.0),
    ("bottle", "bottle",              "count",       1.0,                          0.0),
    ("case",   "case",                "count",       12.0,                         0.0),
    ("count",  "count",               "count",       1.0,                          0.0),
    ("cph",    "components per hour", "count",       1.0,                          0.0),
    ("RPM",    "revolutions per minute", "count",    1.0 / 60.0,                   0.0),
    ("bottle/min", "bottles per minute", "count",   1.0,                          0.0),
    ("label/min",  "labels per minute",  "count",   1.0,                          0.0),
]

# ── Quotient units (left / right) ───────────────────────────────────
# (symbol, name, left_symbol, right_symbol)
BUILTIN_QUOTIENTS: list[tuple[str, str, str, str]] = [
    # Mass flow
    ("kg/s",   "kilograms per second",  "kg", "s"),
    ("kg/h",   "kilograms per hour",    "kg", "h"),
    ("g/s",    "grams per second",      "g",  "s"),
    # Speed / velocity
    ("m/s",    "meters per second",     "m",  "s"),
    ("m/min",  "meters per minute",     "m",  "min"),
    ("m/h",    "meters per hour",       "m",  "h"),
    ("mm/s",   "millimeters per second","mm", "s"),
    ("mm/min", "millimeters per minute","mm", "min"),
    ("ft/s",   "feet per second",       "ft", "s"),
    ("ft/min", "feet per minute",       "ft", "min"),
    ("ft/h",   "feet per hour",         "ft", "h"),
    # Volume flow rate
    ("L/h",    "liters per hour",        "L",  "h"),
    ("L/min",  "liters per minute",      "L",  "min"),
    ("mL/h",   "milliliters per hour",   "mL", "h"),
    # Production rate
    ("EA/s",   "each per second",       "EA", "s"),
    ("EA/min", "each per minute",       "EA", "min"),
    ("EA/h",   "each per hour",         "EA", "h"),
    ("PC/h",   "pieces per hour",       "PC", "h"),
]

# ── Power units (base ^ exponent) ───────────────────────────────────
# (symbol, name, base_symbol, exponent)
BUILTIN_POWERS: list[tuple[str, str, str, int]] = [
    ("m²",   "square meter",         "m",  2),
    ("m³",   "cubic meter",          "m",  3),
    ("cm²",  "square centimeter",    "cm", 2),
    ("cm³",  "cubic centimeter",     "cm", 3),
    ("mm²",  "square millimeter",    "mm", 2),
    ("mm³",  "cubic millimeter",     "mm", 3),
    ("ft²",  "square foot",          "ft", 2),
    ("ft³",  "cubic foot",           "ft", 3),
    ("in²",  "square inch",          "in", 2),
    ("in³",  "cubic inch",           "in", 3),
]


def get_builtin_scalar_dicts() -> list[dict]:
    """Return scalar built-in units as dicts ready for ``UnitOfMeasure(**d)``."""
    return [
        {
            "symbol": symbol,
            "name": name,
            "uom_type": uom_type,
            "uom_class": "scalar",
            "multiplier": multiplier,
            "offset": offset,
            "is_builtin": True,
        }
        for symbol, name, uom_type, multiplier, offset in BUILTIN_SCALARS
    ]


def get_builtin_composite_dicts(symbol_to_id: dict[str, UUID]) -> list[dict]:
    """Return quotient and power built-in units as dicts.

    *symbol_to_id* must map scalar-unit symbols to their database UUIDs
    (populated after scalars are flushed).
    """
    result: list[dict] = []

    for symbol, name, left_sym, right_sym in BUILTIN_QUOTIENTS:
        left_uom = symbol_to_id[left_sym]
        result.append({
            "symbol": symbol,
            "name": name,
            "uom_type": symbol_to_id.get(f"__type__{left_sym}", "other"),  # resolved below
            "uom_class": "quotient",
            "multiplier": 1.0,
            "offset": 0.0,
            "left_uom_id": left_uom,
            "right_uom_id": symbol_to_id[right_sym],
            "is_builtin": True,
        })

    for symbol, name, base_sym, exp in BUILTIN_POWERS:
        result.append({
            "symbol": symbol,
            "name": name,
            "uom_type": symbol_to_id.get(f"__type__{base_sym}", "length"),  # resolved below
            "uom_class": "power",
            "multiplier": 1.0,
            "offset": 0.0,
            "left_uom_id": symbol_to_id[base_sym],
            "exponent": exp,
            "is_builtin": True,
        })

    return result


def get_builtin_composite_dicts_typed(
    symbol_to_uom: dict[str, tuple[UUID, str]],
) -> list[dict]:
    """Return quotient and power built-in units with correct uom_type.

    *symbol_to_uom* maps symbol → (uuid, uom_type).
    """
    result: list[dict] = []

    for symbol, name, left_sym, right_sym in BUILTIN_QUOTIENTS:
        left_id, left_type = symbol_to_uom[left_sym]
        right_id, _ = symbol_to_uom[right_sym]
        result.append({
            "symbol": symbol,
            "name": name,
            "uom_type": left_type,
            "uom_class": "quotient",
            "multiplier": 1.0,
            "offset": 0.0,
            "left_uom_id": left_id,
            "right_uom_id": right_id,
            "is_builtin": True,
        })

    for symbol, name, base_sym, exp in BUILTIN_POWERS:
        base_id, base_type = symbol_to_uom[base_sym]
        result.append({
            "symbol": symbol,
            "name": name,
            "uom_type": base_type,
            "uom_class": "power",
            "multiplier": 1.0,
            "offset": 0.0,
            "left_uom_id": base_id,
            "exponent": exp,
            "is_builtin": True,
        })

    return result


# ── Compatibility aliases ────────────────────────────────────────────
#
# BUILTIN_UNITS is a flattened scalar list where the "fl oz" symbol
# (which contains a space) is normalised to "fl_oz".  This avoids
# symbol-uniqueness issues when the list is used as a lookup key.
#
BUILTIN_UNITS: list[tuple[str, str, str, float, float]] = [
    (sym.replace(" ", "_"), name, uom_type, multiplier, offset)
    for sym, name, uom_type, multiplier, offset in BUILTIN_SCALARS
]

# Rate units are the quotient (left / right) built-ins.
BUILTIN_RATE_UNITS: list[tuple[str, str, str, str]] = BUILTIN_QUOTIENTS


def get_builtin_unit_dicts() -> list[dict]:
    """Return BUILTIN_UNITS as dicts ready for ``UnitOfMeasure(**d)``."""
    return [
        {
            "symbol": symbol,
            "name": name,
            "uom_type": uom_type,
            "uom_class": "scalar",
            "multiplier": multiplier,
            "offset": offset,
            "is_builtin": True,
        }
        for symbol, name, uom_type, multiplier, offset in BUILTIN_UNITS
    ]


def get_builtin_rate_unit_dicts(symbol_to_id: dict) -> list[dict]:
    """Return BUILTIN_RATE_UNITS as dicts with resolved FK IDs.

    *symbol_to_id* must map scalar-unit symbols to their database UUIDs.
    """
    return [
        {
            "symbol": symbol,
            "name": name,
            "uom_type": "rate",
            "uom_class": "quotient",
            "multiplier": 1.0,
            "offset": 0.0,
            "numerator_uom_id": symbol_to_id[left_sym],
            "denominator_uom_id": symbol_to_id[right_sym],
            "is_builtin": True,
        }
        for symbol, name, left_sym, right_sym in BUILTIN_RATE_UNITS
    ]

