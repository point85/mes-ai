"""
UOM: Business logic service for units of measure.

Provides CRUD operations and unit conversion.

Conversion formulas:
  scalar:   base_value  = value * from.multiplier + from.offset
            result      = (base_value - to.offset) / to.multiplier
  quotient: result = value × (left_factor / right_factor)
  product:  result = value × left_factor × right_factor
  power:    result = value × (scalar_factor ^ exponent)

Two units are compatible when:
  scalar   — same uom_type
  quotient — left types match AND right types match
  product  — left types match AND right types match
  power    — base (left) types match AND exponents match
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        stmt = (
            select(UnitOfMeasure)
            .where(UnitOfMeasure.is_active.is_(True))
            .options(
                selectinload(UnitOfMeasure.left_uom),
                selectinload(UnitOfMeasure.right_uom),
            )
        )
        if uom_type is not None:
            stmt = stmt.where(UnitOfMeasure.uom_type == uom_type)
        return await paginate_query(session, stmt, UnitOfMeasure, params)

    @staticmethod
    async def get_uom(session: AsyncSession, uom_id: UUID) -> UnitOfMeasure:
        """Get a unit by ID. Raises NotFoundException if missing or inactive."""
        stmt = (
            select(UnitOfMeasure)
            .where(
                UnitOfMeasure.id == uom_id,
                UnitOfMeasure.is_active.is_(True),
            )
            .options(
                selectinload(UnitOfMeasure.left_uom),
                selectinload(UnitOfMeasure.right_uom),
            )
        )
        result = await session.execute(stmt)
        uom = result.scalar_one_or_none()
        if uom is None:
            raise NotFoundException(resource="UnitOfMeasure", resource_id=str(uom_id))
        return uom

    @staticmethod
    async def get_by_symbol(session: AsyncSession, symbol: str) -> UnitOfMeasure:
        """Get a unit by symbol. Raises NotFoundException if missing."""
        stmt = (
            select(UnitOfMeasure)
            .where(
                UnitOfMeasure.symbol == symbol,
                UnitOfMeasure.is_active.is_(True),
            )
            .options(
                selectinload(UnitOfMeasure.left_uom),
                selectinload(UnitOfMeasure.right_uom),
            )
        )
        result = await session.execute(stmt)
        uom = result.scalar_one_or_none()
        if uom is None:
            raise NotFoundException(resource="UnitOfMeasure", resource_id=symbol)
        return uom

    # ─── Composite UoM helpers ───────────────────────────────────────

    @staticmethod
    async def _resolve_composite_components(
        session: AsyncSession,
        kwargs: dict[str, Any],
    ) -> None:
        """Pop left/right symbol keys and set corresponding ID keys.

        Handles quotient, product, and power classes.
        """
        left_symbol = kwargs.pop("left_uom_symbol", None)
        right_symbol = kwargs.pop("right_uom_symbol", None)
        if left_symbol:
            left_uom = await UoMService.get_by_symbol(session, left_symbol)
            kwargs["left_uom_id"] = left_uom.id
            # Set uom_type from the left component's type
            if "uom_type" not in kwargs or not kwargs["uom_type"]:
                kwargs["uom_type"] = left_uom.uom_type
        if right_symbol:
            right_uom = await UoMService.get_by_symbol(session, right_symbol)
            kwargs["right_uom_id"] = right_uom.id

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_uom(session: AsyncSession, **kwargs: Any) -> UnitOfMeasure:
        """Create a new unit. Raises DuplicateSymbolException if symbol exists."""
        existing = await session.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.symbol == kwargs["symbol"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateSymbolException(kwargs["symbol"])

        await UoMService._resolve_composite_components(session, kwargs)

        uom = UnitOfMeasure(**kwargs)
        session.add(uom)
        await session.flush()

        # Eagerly load composite relationships so Pydantic can read them synchronously
        if uom.left_uom_id is not None:
            await session.refresh(uom, attribute_names=["left_uom", "right_uom"])

        await event_bus.publish(
            uom_created(str(uom.id), uom.symbol, uom.uom_type)
        )
        logger.info("Created UoM %s (%s, type=%s, class=%s)", uom.id, uom.symbol, uom.uom_type, uom.uom_class)
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

        await UoMService._resolve_composite_components(session, kwargs)

        for key, value in kwargs.items():
            if value is not None:
                setattr(uom, key, value)
        await session.flush()

        # Eagerly load composite relationships so Pydantic can read them synchronously
        if uom.left_uom_id is not None:
            await session.refresh(uom, attribute_names=["left_uom", "right_uom"])

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
        """Affine conversion between two scalar units of the same type."""
        base_value = value * from_uom.multiplier + from_uom.offset
        return (base_value - to_uom.offset) / to_uom.multiplier

    @staticmethod
    def convert(
        value: float,
        from_uom: UnitOfMeasure,
        to_uom: UnitOfMeasure,
    ) -> float:
        """
        Convert *value* from one unit to another.

        Both units must share the same uom_class and compatible component types.

        scalar:   standard affine formula
        quotient: result = value × (left_factor / right_factor)
        product:  result = value × left_factor × right_factor
        power:    result = value × (scalar_factor ^ exponent)
        """
        if from_uom.uom_class != to_uom.uom_class:
            raise IncompatibleUoMTypeException(
                from_symbol=from_uom.symbol,
                from_type=f"{from_uom.uom_class}",
                to_symbol=to_uom.symbol,
                to_type=f"{to_uom.uom_class}",
            )

        if from_uom.symbol == to_uom.symbol:
            return value

        cls = from_uom.uom_class

        if cls == "scalar":
            if from_uom.uom_type != to_uom.uom_type:
                raise IncompatibleUoMTypeException(
                    from_symbol=from_uom.symbol,
                    from_type=from_uom.uom_type,
                    to_symbol=to_uom.symbol,
                    to_type=to_uom.uom_type,
                )
            return UoMService._convert_affine(value, from_uom, to_uom)

        if cls in ("quotient", "product"):
            left_from = from_uom.left_uom
            left_to = to_uom.left_uom
            right_from = from_uom.right_uom
            right_to = to_uom.right_uom

            if left_from.uom_type != left_to.uom_type:
                raise IncompatibleUoMTypeException(
                    from_symbol=left_from.symbol,
                    from_type=left_from.uom_type,
                    to_symbol=left_to.symbol,
                    to_type=left_to.uom_type,
                )
            if right_from.uom_type != right_to.uom_type:
                raise IncompatibleUoMTypeException(
                    from_symbol=right_from.symbol,
                    from_type=right_from.uom_type,
                    to_symbol=right_to.symbol,
                    to_type=right_to.uom_type,
                )

            left_factor = UoMService._convert_affine(1.0, left_from, left_to)
            right_factor = UoMService._convert_affine(1.0, right_from, right_to)

            if cls == "quotient":
                return value * left_factor / right_factor
            else:  # product
                return value * left_factor * right_factor

        if cls == "power":
            base_from = from_uom.left_uom
            base_to = to_uom.left_uom
            exp_from = from_uom.exponent
            exp_to = to_uom.exponent

            if base_from.uom_type != base_to.uom_type:
                raise IncompatibleUoMTypeException(
                    from_symbol=base_from.symbol,
                    from_type=base_from.uom_type,
                    to_symbol=base_to.symbol,
                    to_type=base_to.uom_type,
                )
            if exp_from != exp_to:
                raise IncompatibleUoMTypeException(
                    from_symbol=from_uom.symbol,
                    from_type=f"power^{exp_from}",
                    to_symbol=to_uom.symbol,
                    to_type=f"power^{exp_to}",
                )

            scalar_factor = UoMService._convert_affine(1.0, base_from, base_to)
            return value * (scalar_factor ** exp_from)

        # Should not reach here
        raise IncompatibleUoMTypeException(
            from_symbol=from_uom.symbol,
            from_type=from_uom.uom_class,
            to_symbol=to_uom.symbol,
            to_type=to_uom.uom_class,
        )

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
