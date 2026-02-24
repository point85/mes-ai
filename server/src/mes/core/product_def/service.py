"""
PROD-DEF: Business logic service for the product definition domain.

Provides CRUD operations for ProductDefinition, BillOfMaterial, BOMItem,
ProcessRoute, RouteStep, StepParameter.
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

from .events import bom_created, product_created, route_created
from .exceptions import DuplicateProductException
from .models import (
    BillOfMaterial,
    BOMItem,
    ProcessRoute,
    ProductDefinition,
    RouteStep,
    StepParameter,
)

logger = logging.getLogger("mes.product_def")


class ProductDefService:
    """Service class for product definition CRUD operations."""

    # ─── ProductDefinition operations ────────────────────────────────

    @staticmethod
    async def list_products(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[ProductDefinition], str | None, bool]:
        """List active products with pagination."""
        stmt = select(ProductDefinition).where(ProductDefinition.is_active.is_(True))
        return await paginate_query(session, stmt, ProductDefinition, params)

    @staticmethod
    async def get_product(session: AsyncSession, product_id: UUID) -> ProductDefinition:
        """Get a product by ID."""
        stmt = select(ProductDefinition).where(
            ProductDefinition.id == product_id,
            ProductDefinition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException(resource="ProductDefinition", resource_id=str(product_id))
        return product

    @staticmethod
    async def create_product(session: AsyncSession, **kwargs: Any) -> ProductDefinition:
        """Create a new product definition. Checks code+version uniqueness."""
        existing = await session.execute(
            select(ProductDefinition).where(
                ProductDefinition.code == kwargs["code"],
                ProductDefinition.version == kwargs.get("version", "1.0"),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateProductException(kwargs["code"], kwargs.get("version", "1.0"))

        product = ProductDefinition(**kwargs)
        session.add(product)
        await session.flush()

        await event_bus.publish(
            product_created(str(product.id), product.code, product.version)
        )
        logger.info("Created product %s (code=%s v=%s)", product.id, product.code, product.version)
        return product

    @staticmethod
    async def update_product(
        session: AsyncSession, product_id: UUID, **kwargs: Any
    ) -> ProductDefinition:
        """Update a product definition."""
        product = await ProductDefService.get_product(session, product_id)

        code = kwargs.get("code", product.code) or product.code
        version = kwargs.get("version", product.version) or product.version
        if code != product.code or version != product.version:
            existing = await session.execute(
                select(ProductDefinition).where(
                    ProductDefinition.code == code,
                    ProductDefinition.version == version,
                    ProductDefinition.id != product_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateProductException(code, version)

        for key, value in kwargs.items():
            if value is not None:
                setattr(product, key, value)
        await session.flush()
        return product

    # ─── BillOfMaterial operations ───────────────────────────────────

    @staticmethod
    async def list_boms(
        session: AsyncSession,
        product_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[BillOfMaterial], str | None, bool]:
        """List BOMs for a product."""
        await ProductDefService.get_product(session, product_id)
        stmt = select(BillOfMaterial).where(
            BillOfMaterial.product_id == product_id,
            BillOfMaterial.is_active.is_(True),
        )
        return await paginate_query(session, stmt, BillOfMaterial, params)

    @staticmethod
    async def get_bom(session: AsyncSession, bom_id: UUID) -> BillOfMaterial:
        """Get a BOM by ID."""
        stmt = select(BillOfMaterial).where(
            BillOfMaterial.id == bom_id,
            BillOfMaterial.is_active.is_(True),
        )
        result = await session.execute(stmt)
        bom = result.scalar_one_or_none()
        if bom is None:
            raise NotFoundException(resource="BillOfMaterial", resource_id=str(bom_id))
        return bom

    @staticmethod
    async def create_bom(
        session: AsyncSession, product_id: UUID, **kwargs: Any
    ) -> BillOfMaterial:
        """Create a new BOM for a product."""
        await ProductDefService.get_product(session, product_id)

        bom = BillOfMaterial(product_id=product_id, **kwargs)
        session.add(bom)
        await session.flush()

        await event_bus.publish(
            bom_created(str(bom.id), str(product_id), bom.version)
        )
        logger.info("Created BOM %s (v=%s) for product %s", bom.id, bom.version, product_id)
        return bom

    @staticmethod
    async def update_bom(
        session: AsyncSession, bom_id: UUID, **kwargs: Any
    ) -> BillOfMaterial:
        """Update a BOM."""
        bom = await ProductDefService.get_bom(session, bom_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(bom, key, value)
        await session.flush()
        return bom

    # ─── BOMItem operations ──────────────────────────────────────────

    @staticmethod
    async def list_bom_items(
        session: AsyncSession,
        bom_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[BOMItem], str | None, bool]:
        """List items within a BOM."""
        await ProductDefService.get_bom(session, bom_id)
        stmt = select(BOMItem).where(
            BOMItem.bom_id == bom_id,
            BOMItem.is_active.is_(True),
        )
        return await paginate_query(session, stmt, BOMItem, params)

    @staticmethod
    async def create_bom_item(
        session: AsyncSession, bom_id: UUID, **kwargs: Any
    ) -> BOMItem:
        """Create a new BOM item within a BOM."""
        await ProductDefService.get_bom(session, bom_id)
        item = BOMItem(bom_id=bom_id, **kwargs)
        session.add(item)
        await session.flush()
        logger.info("Created BOM item %s in BOM %s", item.id, bom_id)
        return item

    # ─── ProcessRoute operations ─────────────────────────────────────

    @staticmethod
    async def list_routes(
        session: AsyncSession,
        product_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[ProcessRoute], str | None, bool]:
        """List routes for a product."""
        await ProductDefService.get_product(session, product_id)
        stmt = select(ProcessRoute).where(
            ProcessRoute.product_id == product_id,
            ProcessRoute.is_active.is_(True),
        )
        return await paginate_query(session, stmt, ProcessRoute, params)

    @staticmethod
    async def get_route(session: AsyncSession, route_id: UUID) -> ProcessRoute:
        """Get a route by ID."""
        stmt = select(ProcessRoute).where(
            ProcessRoute.id == route_id,
            ProcessRoute.is_active.is_(True),
        )
        result = await session.execute(stmt)
        route = result.scalar_one_or_none()
        if route is None:
            raise NotFoundException(resource="ProcessRoute", resource_id=str(route_id))
        return route

    @staticmethod
    async def create_route(
        session: AsyncSession, product_id: UUID, **kwargs: Any
    ) -> ProcessRoute:
        """Create a new route for a product."""
        await ProductDefService.get_product(session, product_id)

        # If marking as default, unset any existing default
        if kwargs.get("is_default"):
            await ProductDefService._unset_default_route(session, product_id)

        route = ProcessRoute(product_id=product_id, **kwargs)
        session.add(route)
        await session.flush()

        await event_bus.publish(
            route_created(str(route.id), str(product_id), route.name)
        )
        logger.info("Created route %s (%s) for product %s", route.id, route.name, product_id)
        return route

    @staticmethod
    async def update_route(
        session: AsyncSession, route_id: UUID, **kwargs: Any
    ) -> ProcessRoute:
        """Update a route."""
        route = await ProductDefService.get_route(session, route_id)

        # If setting as default, unset any existing default
        if kwargs.get("is_default"):
            await ProductDefService._unset_default_route(session, route.product_id)

        for key, value in kwargs.items():
            if value is not None:
                setattr(route, key, value)
        await session.flush()
        return route

    @staticmethod
    async def _unset_default_route(
        session: AsyncSession, product_id: UUID
    ) -> None:
        """Unset the is_default flag on the current default route for a product."""
        stmt = select(ProcessRoute).where(
            ProcessRoute.product_id == product_id,
            ProcessRoute.is_default.is_(True),
            ProcessRoute.is_active.is_(True),
        )
        result = await session.execute(stmt)
        current_default = result.scalar_one_or_none()
        if current_default is not None:
            current_default.is_default = False

    @staticmethod
    async def get_route_with_steps(
        session: AsyncSession, route_id: UUID
    ) -> ProcessRoute:
        """Get a route with its steps eagerly loaded."""
        stmt = (
            select(ProcessRoute)
            .where(ProcessRoute.id == route_id, ProcessRoute.is_active.is_(True))
            .options(selectinload(ProcessRoute.steps))
        )
        result = await session.execute(stmt)
        route = result.scalar_one_or_none()
        if route is None:
            raise NotFoundException(resource="ProcessRoute", resource_id=str(route_id))
        return route

    # ─── RouteStep operations ────────────────────────────────────────

    @staticmethod
    async def list_steps(
        session: AsyncSession,
        route_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[RouteStep], str | None, bool]:
        """List steps within a route."""
        await ProductDefService.get_route(session, route_id)
        stmt = select(RouteStep).where(
            RouteStep.route_id == route_id,
            RouteStep.is_active.is_(True),
        )
        return await paginate_query(session, stmt, RouteStep, params)

    @staticmethod
    async def get_step(session: AsyncSession, step_id: UUID) -> RouteStep:
        """Get a route step by ID."""
        stmt = select(RouteStep).where(
            RouteStep.id == step_id,
            RouteStep.is_active.is_(True),
        )
        result = await session.execute(stmt)
        step = result.scalar_one_or_none()
        if step is None:
            raise NotFoundException(resource="RouteStep", resource_id=str(step_id))
        return step

    @staticmethod
    async def create_step(
        session: AsyncSession, route_id: UUID, **kwargs: Any
    ) -> RouteStep:
        """Create a new step within a route."""
        await ProductDefService.get_route(session, route_id)
        step = RouteStep(route_id=route_id, **kwargs)
        session.add(step)
        await session.flush()
        logger.info("Created step %s (seq=%s) in route %s", step.id, step.sequence, route_id)
        return step

    @staticmethod
    async def update_step(
        session: AsyncSession, step_id: UUID, **kwargs: Any
    ) -> RouteStep:
        """Update a route step."""
        step = await ProductDefService.get_step(session, step_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(step, key, value)
        await session.flush()
        return step

    # ─── StepParameter operations ────────────────────────────────────

    @staticmethod
    async def list_step_parameters(
        session: AsyncSession,
        step_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[StepParameter], str | None, bool]:
        """List parameters for a step."""
        await ProductDefService.get_step(session, step_id)
        stmt = select(StepParameter).where(
            StepParameter.step_id == step_id,
            StepParameter.is_active.is_(True),
        )
        return await paginate_query(session, stmt, StepParameter, params)

    @staticmethod
    async def create_step_parameter(
        session: AsyncSession, step_id: UUID, **kwargs: Any
    ) -> StepParameter:
        """Create a new parameter specification for a step."""
        await ProductDefService.get_step(session, step_id)
        param = StepParameter(step_id=step_id, **kwargs)
        session.add(param)
        await session.flush()
        logger.info("Created step parameter %s (%s) for step %s", param.id, param.name, step_id)
        return param
