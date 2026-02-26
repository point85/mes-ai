"""
GENEALOGY: Product Genealogy/Traceability module.

Builds the full as-built record for a unit or lot by traversing existing
records: UnitHistory/LotHistory, MaterialConsumption, TestResult, DataPoint.
No separate genealogy tables — this is a pure query module.
"""
