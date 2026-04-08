"""
MAT-MGMT: Business logic service for material management.

Provides CRUD for material definitions and lots, material consumption
recording, and inventory-quantity management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import material_consumed, material_lot_created
from .exceptions import (
    DuplicateLotNumberException,
    DuplicateMaterialCodeException,
    InsufficientQuantityException,
    MaterialLotNotAvailableException,
)
from .models import MaterialConsumption, MaterialDefinition, MaterialLot

logger = logging.getLogger("mes.material")


class MaterialService:
    """Service class for material-definition CRUD."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_materials(
        session: AsyncSession,
        params: PaginationParams,
        material_type: str | None = None,
    ) -> tuple[Sequence[MaterialDefinition], str | None, bool]:
        """List active material definitions with optional type filter."""
        stmt = select(MaterialDefinition).where(
            MaterialDefinition.is_active.is_(True),
        )
        if material_type is not None:
            stmt = stmt.where(MaterialDefinition.material_type == material_type)
        return await paginate_query(session, stmt, MaterialDefinition, params)

    @staticmethod
    async def get_material(
        session: AsyncSession, material_id: UUID,
    ) -> MaterialDefinition:
        """Get a material definition by ID. Raises NotFoundException if missing."""
        stmt = select(MaterialDefinition).where(
            MaterialDefinition.id == material_id,
            MaterialDefinition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        material = result.scalar_one_or_none()
        if material is None:
            raise NotFoundException(
                resource="MaterialDefinition", resource_id=str(material_id),
            )
        return material

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_material(
        session: AsyncSession, **kwargs: Any,
    ) -> MaterialDefinition:
        """Create a new material definition. Raises DuplicateMaterialCodeException if code exists."""
        existing = await session.execute(
            select(MaterialDefinition).where(
                MaterialDefinition.code == kwargs["code"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateMaterialCodeException(kwargs["code"])

        material = MaterialDefinition(**kwargs)
        session.add(material)
        await session.flush()

        logger.info(
            "Created material definition %s (%s)",
            material.id, material.code,
        )
        return material

    @staticmethod
    async def update_material(
        session: AsyncSession, material_id: UUID, **kwargs: Any,
    ) -> MaterialDefinition:
        """Update a material definition. Only non-None values are applied."""
        material = await MaterialService.get_material(session, material_id)

        # Check code uniqueness if changing
        new_code = kwargs.get("code")
        if new_code is not None and new_code != material.code:
            existing = await session.execute(
                select(MaterialDefinition).where(
                    MaterialDefinition.code == new_code,
                    MaterialDefinition.id != material_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateMaterialCodeException(new_code)

        for key, value in kwargs.items():
            if value is not None:
                setattr(material, key, value)
        await session.flush()

        logger.info(
            "Updated material definition %s (%s)", material.id, material.code,
        )
        return material

    @staticmethod
    async def delete_material(
        session: AsyncSession, material_id: UUID,
    ) -> None:
        """Soft-delete a material definition."""
        material = await MaterialService.get_material(session, material_id)
        material.is_active = False
        await session.flush()
        logger.info(
            "Soft-deleted material definition %s (%s)", material.id, material.code,
        )


class MaterialLotService:
    """Service class for material-lot CRUD and consumption."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_lots(
        session: AsyncSession,
        params: PaginationParams,
        material_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[Sequence[MaterialLot], str | None, bool]:
        """List active material lots with optional filters."""
        stmt = select(MaterialLot).where(MaterialLot.is_active.is_(True))
        if material_id is not None:
            stmt = stmt.where(MaterialLot.material_id == material_id)
        if status is not None:
            stmt = stmt.where(MaterialLot.status == status)
        return await paginate_query(session, stmt, MaterialLot, params)

    @staticmethod
    async def get_lot(
        session: AsyncSession, lot_id: UUID,
    ) -> MaterialLot:
        """Get a material lot by ID. Raises NotFoundException if missing."""
        stmt = select(MaterialLot).where(
            MaterialLot.id == lot_id,
            MaterialLot.is_active.is_(True),
        )
        result = await session.execute(stmt)
        lot = result.scalar_one_or_none()
        if lot is None:
            raise NotFoundException(
                resource="MaterialLot", resource_id=str(lot_id),
            )
        return lot

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_lot(
        session: AsyncSession, **kwargs: Any,
    ) -> MaterialLot:
        """Create a new material lot. Raises DuplicateLotNumberException if lot_number exists."""
        existing = await session.execute(
            select(MaterialLot).where(
                MaterialLot.lot_number == kwargs["lot_number"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateLotNumberException(kwargs["lot_number"])

        lot = MaterialLot(**kwargs)
        session.add(lot)
        await session.flush()

        await event_bus.publish(
            material_lot_created(
                str(lot.id),
                str(lot.material_id),
                lot.lot_number,
                lot.quantity_on_hand,
            )
        )
        logger.info(
            "Created material lot %s (%s) qty=%s",
            lot.id, lot.lot_number, lot.quantity_on_hand,
        )
        return lot

    @staticmethod
    async def update_lot(
        session: AsyncSession, lot_id: UUID, **kwargs: Any,
    ) -> MaterialLot:
        """Update a material lot. Only non-None values are applied."""
        lot = await MaterialLotService.get_lot(session, lot_id)

        # Check lot_number uniqueness if changing
        new_number = kwargs.get("lot_number")
        if new_number is not None and new_number != lot.lot_number:
            existing = await session.execute(
                select(MaterialLot).where(
                    MaterialLot.lot_number == new_number,
                    MaterialLot.id != lot_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateLotNumberException(new_number)

        for key, value in kwargs.items():
            if value is not None:
                setattr(lot, key, value)
        await session.flush()

        logger.info("Updated material lot %s (%s)", lot.id, lot.lot_number)
        return lot

    # ─── Consumption ─────────────────────────────────────────────────

    @staticmethod
    async def consume(
        session: AsyncSession,
        lot_id: UUID,
        *,
        unit_id: UUID | None = None,
        lot_wip_id: UUID | None = None,
        step_id: UUID | None = None,
        quantity_consumed: float,
    ) -> MaterialConsumption:
        """
        Record material consumption from a material lot.

        Decrements quantity_on_hand, creates a MaterialConsumption record,
        and marks the lot as 'consumed' if on-hand reaches 0.
        """
        lot = await MaterialLotService.get_lot(session, lot_id)

        if lot.status not in ("available", "reserved"):
            raise MaterialLotNotAvailableException(lot.lot_number, lot.status)

        available = lot.quantity_on_hand
        if quantity_consumed > available:
            raise InsufficientQuantityException(
                lot.lot_number, quantity_consumed, available,
            )

        # Decrement on-hand
        lot.quantity_on_hand -= quantity_consumed
        if lot.quantity_on_hand <= 0:
            lot.quantity_on_hand = 0.0
            lot.status = "consumed"

        # Create consumption record
        now = datetime.now(timezone.utc)
        consumption = MaterialConsumption(
            material_lot_id=lot.id,
            unit_id=unit_id,
            lot_id=lot_wip_id,
            step_id=step_id,
            quantity_consumed=quantity_consumed,
            consumed_at=now,
            consumed_at_utc=now.replace(tzinfo=None),
        )
        session.add(consumption)
        await session.flush()

        await event_bus.publish(
            material_consumed(
                str(lot.id),
                str(unit_id) if unit_id else None,
                quantity_consumed,
            )
        )
        logger.info(
            "Consumed %.3f from lot %s (%s) → on_hand=%.3f",
            quantity_consumed, lot.id, lot.lot_number, lot.quantity_on_hand,
        )
        return consumption

    @staticmethod
    async def get_consumptions_for_unit(
        session: AsyncSession, unit_id: UUID,
    ) -> Sequence[MaterialConsumption]:
        """Get all consumption records for a given WIP unit."""
        stmt = (
            select(MaterialConsumption)
            .where(MaterialConsumption.unit_id == unit_id)
            .order_by(MaterialConsumption.consumed_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_consumptions_for_lot(
        session: AsyncSession, lot_wip_id: UUID,
    ) -> Sequence[MaterialConsumption]:
        """Get all consumption records for a given WIP lot."""
        stmt = (
            select(MaterialConsumption)
            .where(MaterialConsumption.lot_id == lot_wip_id)
            .order_by(MaterialConsumption.consumed_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
