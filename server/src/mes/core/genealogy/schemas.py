"""
GENEALOGY: Pydantic schemas for the Genealogy/Traceability API.

Output-only schemas representing the as-built record of a unit or lot.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GenealogyStepRecord(BaseModel):
    """A single step in the genealogy — what happened at one route step."""

    step_id: UUID | None = None
    step_sequence: int | None = None
    step_name: str | None = None
    entered_at: datetime | None = None
    entered_at_utc: datetime | None = None
    exited_at: datetime | None = None
    exited_at_utc: datetime | None = None
    result: str | None = None
    equipment_id: UUID | None = None
    equipment_name: str | None = None
    data_snapshot: dict | None = None


class GenealogyMaterialRecord(BaseModel):
    """A material consumed during production."""

    material_lot_id: UUID
    material_code: str | None = None
    material_name: str | None = None
    lot_number: str | None = None
    quantity_consumed: float
    consumed_at: datetime
    consumed_at_utc: datetime | None = None
    step_id: UUID | None = None


class GenealogyDataRecord(BaseModel):
    """A data collection point associated with the unit/lot."""

    data_point_id: UUID
    definition_code: str | None = None
    definition_name: str | None = None
    value_numeric: float | None = None
    value_string: str | None = None
    value_boolean: bool | None = None
    collected_at: datetime
    collected_at_utc: datetime | None = None


class GenealogyRecord(BaseModel):
    """
    The full as-built record for a unit or lot.

    Aggregates all production steps, consumed materials, quality results,
    and collected data into a single traceability document.
    """

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    serial_number: str | None = None
    lot_number: str | None = None
    order_id: UUID | None = None
    order_number: str | None = None
    product_id: UUID | None = None
    product_name: str | None = None
    status: str | None = None

    steps: list[GenealogyStepRecord] = []
    materials: list[GenealogyMaterialRecord] = []
    data_points: list[GenealogyDataRecord] = []
