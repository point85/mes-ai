"""
PHYS-MODEL: Physical Model module.

Implements the ISA-95 physical asset hierarchy:
Site → Area → ProductionLine → WorkCell → Equipment

This module is the foundation for all shop-floor operations — every WIP movement,
data collection, and equipment state change references entities defined here.
"""
