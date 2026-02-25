"""
UOM: Units of Measure module.

Manages unit definitions, type classifications, and conversions.
Supports SI, imperial, and user-defined custom units (e.g. can, case, pallet).

Conversion model:
    Every unit stores a multiplier and offset relative to the base unit of its type.
    base_value = value * multiplier + offset
    To convert A → B (same type):
        b_value = (a_value * a.multiplier + a.offset - b.offset) / b.multiplier
"""
