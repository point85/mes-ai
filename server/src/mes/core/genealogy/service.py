"""
GENEALOGY: Service for building the full as-built traceability record.

Queries across UnitHistory/LotHistory, MaterialConsumption, TestResult,
and DataPoint to assemble the genealogy for a unit or lot.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.framework.api.exceptions import NotFoundException

from mes.core.wip.models import Unit, Lot, UnitHistory, LotHistory
from mes.core.material.models import MaterialConsumption, MaterialDefinition, MaterialLot
from mes.core.quality.models import TestResult, QualityTest
from mes.core.data_collection.models import DataPoint, DataDefinition

from .schemas import (
    GenealogyDataRecord,
    GenealogyMaterialRecord,
    GenealogyRecord,
    GenealogyStepRecord,
    GenealogyTestRecord,
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
        - Processing history (UnitHistory)
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
            select(UnitHistory)
            .where(UnitHistory.unit_id == unit_id)
            .order_by(UnitHistory.entered_at)
        )
        hist_result = await session.execute(hist_stmt)
        histories = hist_result.scalars().all()

        steps = [
            GenealogyStepRecord(
                step_id=h.step_id,
                entered_at=h.entered_at,
                exited_at=h.exited_at,
                result=h.result,
                equipment_id=h.equipment_id,
                data_snapshot=h.data_snapshot,
            )
            for h in histories
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

        # ── Quality test results ────────────────────────────────────
        test_stmt = (
            select(TestResult, QualityTest)
            .join(QualityTest, TestResult.test_id == QualityTest.id)
            .where(TestResult.unit_id == unit_id)
            .order_by(TestResult.tested_at)
        )
        test_result = await session.execute(test_stmt)
        test_rows = test_result.all()

        test_records = [
            GenealogyTestRecord(
                result_id=tr.id,
                test_code=qt.code,
                test_name=qt.name,
                result=tr.result,
                measured_values=tr.measured_values,
                tested_at=tr.tested_at,
                tested_at_utc=tr.tested_at_utc,
                equipment_id=tr.equipment_id,
            )
            for tr, qt in test_rows
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

        return GenealogyRecord(
            unit_id=unit.id,
            serial_number=unit.serial_number,
            order_id=unit.order_id,
            product_id=unit.product_id,
            status=unit.status,
            steps=steps,
            materials=materials,
            test_results=test_records,
            data_points=data_records,
        )

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
            select(LotHistory)
            .where(LotHistory.lot_id == lot_id)
            .order_by(LotHistory.entered_at)
        )
        hist_result = await session.execute(hist_stmt)
        histories = hist_result.scalars().all()

        steps = [
            GenealogyStepRecord(
                step_id=h.step_id,
                entered_at=h.entered_at,
                entered_at_utc=h.entered_at_utc,
                exited_at=h.exited_at,
                exited_at_utc=h.exited_at_utc,
                result=h.result,
                equipment_id=h.equipment_id,
            )
            for h in histories
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

        # ── Quality test results ────────────────────────────────────
        test_stmt = (
            select(TestResult, QualityTest)
            .join(QualityTest, TestResult.test_id == QualityTest.id)
            .where(TestResult.lot_id == lot_id)
            .order_by(TestResult.tested_at)
        )
        test_result = await session.execute(test_stmt)
        test_rows = test_result.all()

        test_records = [
            GenealogyTestRecord(
                result_id=tr.id,
                test_code=qt.code,
                test_name=qt.name,
                result=tr.result,
                measured_values=tr.measured_values,
                tested_at=tr.tested_at,
                tested_at_utc=tr.tested_at_utc,
                equipment_id=tr.equipment_id,
            )
            for tr, qt in test_rows
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

        return GenealogyRecord(
            lot_id=lot.id,
            lot_number=lot.lot_number,
            order_id=lot.order_id,
            product_id=lot.product_id,
            status=lot.status,
            steps=steps,
            materials=materials,
            test_results=test_records,
            data_points=data_records,
        )
