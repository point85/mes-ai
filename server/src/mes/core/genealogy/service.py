"""
GENEALOGY: Service for building the full as-built traceability record.

Queries across SegmentResponseUnit/SegmentResponseLot, MaterialConsumption, TestResult,
and DataPoint to assemble the genealogy for a unit or lot.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.framework.api.exceptions import NotFoundException

from mes.core.wip.models import Unit, Lot, SegmentResponseUnit, SegmentResponseLot
from mes.core.inventory.models import InventoryTransaction, StorageLocation
from mes.core.material.models import MaterialConsumption, MaterialDefinition, MaterialLot
from mes.core.data_collection.models import DataPoint, DataDefinition
from mes.core.operations.models import OperationsRequest
from mes.core.product_def.models import ProductDefinition, ProcessSegment
from mes.core.physical_model.models import Equipment

from .schemas import (
    GenealogyDataRecord,
    GenealogyInventoryRecord,
    GenealogyMaterialRecord,
    GenealogyRecord,
    GenealogyStepRecord,
)

logger = logging.getLogger("mes.genealogy")


class GenealogyService:
    """Builds complete as-built records by traversing existing domain data."""

    @staticmethod
    async def get_unit_genealogy(
        session: AsyncSession, unit_id: UUID,
    ) -> GenealogyRecord:
        """
        Build the full genealogy for a unit.

        Gathers:
        - Processing history (SegmentResponseUnit)
        - Consumed materials (MaterialConsumption)
        - Quality test results (TestResult)
        - Collected data points (DataPoint)
        """
        # ── Fetch unit ──────────────────────────────────────────────
        stmt = select(Unit).where(Unit.id == unit_id)
        result = await session.execute(stmt)
        unit = result.scalar_one_or_none()
        if unit is None:
            raise NotFoundException(resource="Unit", resource_id=str(unit_id))

        # ── Processing history ──────────────────────────────────────
        hist_stmt = (
            select(SegmentResponseUnit, ProcessSegment, Equipment)
            .outerjoin(ProcessSegment, SegmentResponseUnit.step_id == ProcessSegment.id)
            .outerjoin(Equipment, SegmentResponseUnit.equipment_id == Equipment.id)
            .where(SegmentResponseUnit.unit_id == unit_id)
            .order_by(SegmentResponseUnit.entered_at)
        )
        hist_result = await session.execute(hist_stmt)
        histories = hist_result.all()

        steps = [
            GenealogyStepRecord(
                step_id=h.step_id,
                step_sequence=seg.sequence if seg else None,
                step_name=seg.name if seg else None,
                entered_at=h.entered_at,
                exited_at=h.exited_at,
                result=h.result,
                equipment_id=h.equipment_id,
                equipment_name=equip.name if equip else None,
                data_snapshot=h.data_snapshot,
            )
            for h, seg, equip in histories
        ]

        # ── Consumed materials ──────────────────────────────────────
        mat_stmt = (
            select(MaterialConsumption, MaterialLot, MaterialDefinition)
            .join(MaterialLot, MaterialConsumption.material_lot_id == MaterialLot.id)
            .join(MaterialDefinition, MaterialLot.material_id == MaterialDefinition.id)
            .where(MaterialConsumption.unit_id == unit_id)
            .order_by(MaterialConsumption.consumed_at)
        )
        mat_result = await session.execute(mat_stmt)
        mat_rows = mat_result.all()

        materials = [
            GenealogyMaterialRecord(
                material_lot_id=consumption.material_lot_id,
                material_code=mat_def.code,
                material_name=mat_def.name,
                lot_number=lot.lot_number,
                quantity_consumed=consumption.quantity_consumed,
                consumed_at=consumption.consumed_at,
                step_id=consumption.step_id,
            )
            for consumption, lot, mat_def in mat_rows
        ]

        # ── Data points ─────────────────────────────────────────────
        data_stmt = (
            select(DataPoint, DataDefinition)
            .join(DataDefinition, DataPoint.definition_id == DataDefinition.id)
            .where(DataPoint.unit_id == unit_id)
            .order_by(DataPoint.collected_at)
        )
        data_result = await session.execute(data_stmt)
        data_rows = data_result.all()

        data_records = [
            GenealogyDataRecord(
                data_point_id=dp.id,
                definition_code=dd.code,
                definition_name=dd.name,
                value_numeric=dp.value_numeric,
                value_string=dp.value_string,
                value_boolean=dp.value_boolean,
                collected_at=dp.collected_at,
                collected_at_utc=dp.collected_at_utc,
            )
            for dp, dd in data_rows
        ]

        # ── Fetch order and product names ───────────────────────────
        order_number: str | None = None
        product_name: str | None = None
        if unit.order_id:
            order_stmt = select(OperationsRequest.order_number).where(OperationsRequest.id == unit.order_id)
            order_number = (await session.execute(order_stmt)).scalar_one_or_none()
        if unit.product_id:
            product_stmt = select(ProductDefinition.name).where(ProductDefinition.id == unit.product_id)
            product_name = (await session.execute(product_stmt)).scalar_one_or_none()

        inventory = await GenealogyService._inventory_history(
            session, unit.serial_number, unit.id,
        )

        return GenealogyRecord(
            unit_id=unit.id,
            serial_number=unit.serial_number,
            order_id=unit.order_id,
            order_number=order_number,
            product_id=unit.product_id,
            product_name=product_name,
            status=unit.status,
            steps=steps,
            materials=materials,
            inventory_transactions=inventory,
            data_points=data_records,
        )

    @staticmethod
    async def _inventory_history(
        session: AsyncSession, identifier: str, wip_id: UUID,
    ) -> list[GenealogyInventoryRecord]:
        """
        Inventory transactions (transfer to inventory, move, ship, ...) of the
        item created when this WIP was transferred off its route. The item
        shares the WIP's serial/lot number and its receive transaction
        references the WIP.
        """
        lot_stmt = (
            select(MaterialLot.id)
            .join(InventoryTransaction, InventoryTransaction.material_lot_id == MaterialLot.id)
            .where(
                MaterialLot.lot_number == identifier,
                InventoryTransaction.reference_id == wip_id,
            )
            .limit(1)
        )
        material_lot_id = (await session.execute(lot_stmt)).scalar_one_or_none()
        if material_lot_id is None:
            return []

        stmt = (
            select(InventoryTransaction)
            .where(InventoryTransaction.material_lot_id == material_lot_id)
            .order_by(InventoryTransaction.performed_at)
        )
        txns = (await session.execute(stmt)).scalars().all()
        loc_ids = {
            i for t in txns for i in (t.from_location_id, t.to_location_id) if i
        }
        names: dict[UUID, str] = {}
        if loc_ids:
            loc_rows = await session.execute(
                select(StorageLocation.id, StorageLocation.name)
                .where(StorageLocation.id.in_(loc_ids)),
            )
            names = {i: n for i, n in loc_rows.all()}

        return [
            GenealogyInventoryRecord(
                transaction_id=t.id,
                transaction_type=t.transaction_type,
                material_lot_id=t.material_lot_id,
                quantity=t.quantity,
                from_location=names.get(t.from_location_id) if t.from_location_id else None,
                to_location=names.get(t.to_location_id) if t.to_location_id else None,
                reason=t.reason,
                performed_at=t.performed_at,
            )
            for t in txns
        ]

    @staticmethod
    async def get_lot_genealogy(
        session: AsyncSession, lot_id: UUID,
    ) -> GenealogyRecord:
        """
        Build the full genealogy for a lot.

        Same structure as unit genealogy but queries lot-specific tables.
        """
        # ── Fetch lot ───────────────────────────────────────────────
        stmt = select(Lot).where(Lot.id == lot_id)
        result = await session.execute(stmt)
        lot = result.scalar_one_or_none()
        if lot is None:
            raise NotFoundException(resource="Lot", resource_id=str(lot_id))

        # ── Processing history ──────────────────────────────────────
        hist_stmt = (
            select(SegmentResponseLot, ProcessSegment, Equipment)
            .outerjoin(ProcessSegment, SegmentResponseLot.step_id == ProcessSegment.id)
            .outerjoin(Equipment, SegmentResponseLot.equipment_id == Equipment.id)
            .where(SegmentResponseLot.lot_id == lot_id)
            .order_by(SegmentResponseLot.entered_at)
        )
        hist_result = await session.execute(hist_stmt)
        histories = hist_result.all()

        steps = [
            GenealogyStepRecord(
                step_id=h.step_id,
                step_sequence=seg.sequence if seg else None,
                step_name=seg.name if seg else None,
                entered_at=h.entered_at,
                entered_at_utc=h.entered_at_utc,
                exited_at=h.exited_at,
                exited_at_utc=h.exited_at_utc,
                result=h.result,
                equipment_id=h.equipment_id,
                equipment_name=equip.name if equip else None,
                data_snapshot=h.data_snapshot,
            )
            for h, seg, equip in histories
        ]

        # ── Consumed materials ──────────────────────────────────────
        mat_stmt = (
            select(MaterialConsumption, MaterialLot, MaterialDefinition)
            .join(MaterialLot, MaterialConsumption.material_lot_id == MaterialLot.id)
            .join(MaterialDefinition, MaterialLot.material_id == MaterialDefinition.id)
            .where(MaterialConsumption.lot_id == lot_id)
            .order_by(MaterialConsumption.consumed_at)
        )
        mat_result = await session.execute(mat_stmt)
        mat_rows = mat_result.all()

        materials = [
            GenealogyMaterialRecord(
                material_lot_id=consumption.material_lot_id,
                material_code=mat_def.code,
                material_name=mat_def.name,
                lot_number=mat_lot.lot_number,
                quantity_consumed=consumption.quantity_consumed,
                consumed_at=consumption.consumed_at,
                consumed_at_utc=consumption.consumed_at_utc,
                step_id=consumption.step_id,
            )
            for consumption, mat_lot, mat_def in mat_rows
        ]

        # ── Data points ─────────────────────────────────────────────
        data_stmt = (
            select(DataPoint, DataDefinition)
            .join(DataDefinition, DataPoint.definition_id == DataDefinition.id)
            .where(DataPoint.lot_id == lot_id)
            .order_by(DataPoint.collected_at)
        )
        data_result = await session.execute(data_stmt)
        data_rows = data_result.all()

        data_records = [
            GenealogyDataRecord(
                data_point_id=dp.id,
                definition_code=dd.code,
                definition_name=dd.name,
                value_numeric=dp.value_numeric,
                value_string=dp.value_string,
                value_boolean=dp.value_boolean,
                collected_at=dp.collected_at,
                collected_at_utc=dp.collected_at_utc,
            )
            for dp, dd in data_rows
        ]

        # ── Fetch order and product names ───────────────────────────
        order_number: str | None = None
        product_name: str | None = None
        if lot.order_id:
            order_stmt = select(OperationsRequest.order_number).where(OperationsRequest.id == lot.order_id)
            order_number = (await session.execute(order_stmt)).scalar_one_or_none()
        if lot.product_id:
            product_stmt = select(ProductDefinition.name).where(ProductDefinition.id == lot.product_id)
            product_name = (await session.execute(product_stmt)).scalar_one_or_none()

        inventory = await GenealogyService._inventory_history(
            session, lot.lot_number, lot.id,
        )

        return GenealogyRecord(
            lot_id=lot.id,
            lot_number=lot.lot_number,
            order_id=lot.order_id,
            order_number=order_number,
            product_id=lot.product_id,
            product_name=product_name,
            status=lot.status,
            steps=steps,
            materials=materials,
            inventory_transactions=inventory,
            data_points=data_records,
        )
