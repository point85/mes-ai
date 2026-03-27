"""
UOM: Business logic service for units of measure.

Provides CRUD operations and unit conversion.

Conversion formula (affine):
    base_value  = value * from_unit.multiplier + from_unit.offset
    result      = (base_value - to_unit.offset) / to_unit.multiplier

Rate UoMs (uom_type="rate") convert by independently converting the
numerator and denominator components.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import uom_created, uom_updated, uom_deleted
from .exceptions import (
    BuiltinUoMException,
    DuplicateSymbolException,
    IncompatibleUoMTypeException,
)
from .models import UnitOfMeasure

logger = logging.getLogger("mes.uom")


class UoMService:
    """Service class for unit-of-measure CRUD and conversion operations."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_uoms(
        session: AsyncSession,
        params: PaginationParams,
        uom_type: str | None = None,
    ) -> tuple[Sequence[UnitOfMeasure], str | None, bool]:
        """List active units, optionally filtered by type, with pagination."""
        stmt = select(UnitOfMeasure).where(UnitOfMeasure.is_active.is_(True))
        if uom_type is not None:
            stmt = stmt.where(UnitOfMeasure.uom_type == uom_type)
        return await paginate_query(session, stmt, UnitOfMeasure, params)

    @staticmethod
    async def get_uom(session: AsyncSession, uom_id: UUID) -> UnitOfMeasure:
        """Get a unit by ID. Raises NotFoundException if missing or inactive."""
        stmt = select(UnitOfMeasure).where(
            UnitOfMeasure.id == uom_id,
            UnitOfMeasure.is_active.is_(True),
        )
        result = await session.execute(stmt)
        uom = result.scalar_one_or_none()
        if uom is None:
            raise NotFoundException(resource="UnitOfMeasure", resource_id=str(uom_id))
        return uom

    @staticmethod
    async def get_by_symbol(session: AsyncSession, symbol: str) -> UnitOfMeasure:
        """Get a unit by symbol. Raises NotFoundException if missing."""
        stmt = select(UnitOfMeasure).where(
            UnitOfMeasure.symbol == symbol,
            UnitOfMeasure.is_active.is_(True),
        )
        result = await session.execute(stmt)
        uom = result.scalar_one_or_none()
        if uom is None:
            raise NotFoundException(resource="UnitOfMeasure", resource_id=symbol)
        return uom

    # ─── Rate UoM helpers ────────────────────────────────────────────

    @staticmethod
    async def _resolve_rate_components(
        session: AsyncSession,
        kwargs: dict[str, Any],
    ) -> None:
        """Pop numerator/denominator symbol keys and set corresponding ID keys."""
        numerator_symbol = kwargs.pop("numerator_uom_symbol", None)
        denominator_symbol = kwargs.pop("denominator_uom_symbol", None)
        if numerator_symbol:
            num_uom = await UoMService.get_by_symbol(session, numerator_symbol)
            kwargs["numerator_uom_id"] = num_uom.id
        if denominator_symbol:
            den_uom = await UoMService.get_by_symbol(session, denominator_symbol)
            kwargs["denominator_uom_id"] = den_uom.id

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_uom(session: AsyncSession, **kwargs: Any) -> UnitOfMeasure:
        """Create a new unit. Raises DuplicateSymbolException if symbol exists."""
        existing = await session.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.symbol == kwargs["symbol"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateSymbolException(kwargs["symbol"])

        await UoMService._resolve_rate_components(session, kwargs)

        uom = UnitOfMeasure(**kwargs)
        session.add(uom)
        await session.flush()

        await event_bus.publish(
            uom_created(str(uom.id), uom.symbol, uom.uom_type)
        )
        logger.info("Created UoM %s (%s, type=%s)", uom.id, uom.symbol, uom.uom_type)
        return uom

    @staticmethod
    async def update_uom(
        session: AsyncSession, uom_id: UUID, **kwargs: Any
    ) -> UnitOfMeasure:
        """Update a unit's fields. Only non-None values are applied."""
        uom = await UoMService.get_uom(session, uom_id)

        # Check symbol uniqueness if symbol is changing
        new_symbol = kwargs.get("symbol")
        if new_symbol is not None and new_symbol != uom.symbol:
            existing = await session.execute(
                select(UnitOfMeasure).where(
                    UnitOfMeasure.symbol == new_symbol,
                    UnitOfMeasure.id != uom_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateSymbolException(new_symbol)

        await UoMService._resolve_rate_components(session, kwargs)

        for key, value in kwargs.items():
            if value is not None:
                setattr(uom, key, value)
        await session.flush()

        await event_bus.publish(uom_updated(str(uom.id), uom.symbol))
        logger.info("Updated UoM %s (%s)", uom.id, uom.symbol)
        return uom

    @staticmethod
    async def delete_uom(session: AsyncSession, uom_id: UUID) -> None:
        """Soft-delete a unit. Raises BuiltinUoMException for built-in units."""
        uom = await UoMService.get_uom(session, uom_id)
        if uom.is_builtin:
            raise BuiltinUoMException(uom.symbol)

        uom.is_active = False
        await session.flush()

        await event_bus.publish(uom_deleted(str(uom.id), uom.symbol))
        logger.info("Soft-deleted UoM %s (%s)", uom.id, uom.symbol)

    # ─── Conversion ──────────────────────────────────────────────────

    @staticmethod
    def _convert_affine(
        value: float,
        from_uom: UnitOfMeasure,
        to_uom: UnitOfMeasure,
    ) -> float:
        """Simple affine conversion between two non-rate units of the same type."""
        base_value = value * from_uom.multiplier + from_uom.offset
        return (base_value - to_uom.offset) / to_uom.multiplier

    @staticmethod
    def convert(
        value: float,
        from_uom: UnitOfMeasure,
        to_uom: UnitOfMeasure,
    ) -> float:
        """
        Convert *value* from one unit to another (must share the same uom_type).

        For rate UoMs the numerator and denominator are converted independently:
            result = value * (num_factor / den_factor)
        where each factor is an affine conversion of the respective component.
        """
        if from_uom.uom_type != to_uom.uom_type:
            raise IncompatibleUoMTypeException(
                from_symbol=from_uom.symbol,
                from_type=from_uom.uom_type,
                to_symbol=to_uom.symbol,
                to_type=to_uom.uom_type,
            )

        if from_uom.symbol == to_uom.symbol:
            return value

        # Rate-to-rate: convert numerator and denominator independently
        if from_uom.is_rate and to_uom.is_rate:
            num_from = from_uom.numerator_uom
            num_to = to_uom.numerator_uom
            den_from = from_uom.denominator_uom
            den_to = to_uom.denominator_uom

            if num_from.uom_type != num_to.uom_type:
                raise IncompatibleUoMTypeException(
                    from_symbol=num_from.symbol,
                    from_type=num_from.uom_type,
                    to_symbol=num_to.symbol,
                    to_type=num_to.uom_type,
                )
            if den_from.uom_type != den_to.uom_type:
                raise IncompatibleUoMTypeException(
                    from_symbol=den_from.symbol,
                    from_type=den_from.uom_type,
                    to_symbol=den_to.symbol,
                    to_type=den_to.uom_type,
                )

            num_factor = UoMService._convert_affine(1.0, num_from, num_to)
            den_factor = UoMService._convert_affine(1.0, den_from, den_to)
            return value * num_factor / den_factor

        # Standard affine conversion
        return UoMService._convert_affine(value, from_uom, to_uom)

    @staticmethod
    async def convert_by_symbol(
        session: AsyncSession,
        value: float,
        from_symbol: str,
        to_symbol: str,
    ) -> tuple[float, UnitOfMeasure, UnitOfMeasure]:
        """
        Convert *value* looking up units by symbol.

        Returns (converted_value, from_uom, to_uom).
        """
        from_uom = await UoMService.get_by_symbol(session, from_symbol)
        to_uom = await UoMService.get_by_symbol(session, to_symbol)
        result = UoMService.convert(value, from_uom, to_uom)
        return result, from_uom, to_uom
