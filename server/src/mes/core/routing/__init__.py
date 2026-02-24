"""
ROUTE-DEF / ROUTE-ENGINE: Routing module.

Route *definition* models (ProcessRoute, RouteStep, StepParameter) live in
the product_def module since they are tightly coupled to ProductDefinition.

This module will house the ROUTE-ENGINE (Layer 2) — runtime logic for:
- Determining the next step for a unit/lot
- Handling rework loops and step skipping
- Alternate route selection based on equipment availability
"""
