"""
PROD-DEF: Business logic service for the product definition domain.

Provides CRUD operations for ProductDefinition, BillOfMaterial, BOMItem,
OperationsDefinition, ProcessSegment, SegmentParameter, plus disposition
list management on ProcessSegment (input/output dispositions, which
together define the route graph).
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, select
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
    Disposition,
    OperationsDefinition,
    ProductDefinition,
    OperationsDefinitionMaterialAssignment,
    OperationsDefinitionProductAssignment,
    ProcessSegment,
    ProcessSegmentInputDisposition,
    ProcessSegmentOutputDisposition,
    SegmentEquipmentRequirement,
    SegmentMaterialRequirement,
    SegmentParameter,
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

    @staticmethod
    async def delete_product(session: AsyncSession, product_id: UUID) -> None:
        """Soft-delete a product definition."""
        product = await ProductDefService.get_product(session, product_id)
        product.is_active = False
        await session.flush()
        logger.info("Soft-deleted product %s (%s v%s)", product.id, product.code, product.version)

    @staticmethod
    async def clone_product(
        session: AsyncSession,
        source_id: UUID,
        code: str,
        name: str,
        version: str = "1.0",
        description: str | None = None,
    ) -> ProductDefinition:
        """Deep-clone a product: copies BOMs (with items) and routes (with steps, parameters, transitions)."""
        source = await ProductDefService.get_product(session, source_id)

        # Check uniqueness of new code+version
        existing = await session.execute(
            select(ProductDefinition).where(
                ProductDefinition.code == code,
                ProductDefinition.version == version,
            )
        )
        if existing.scalar_one_or_none() is not None:
            from .exceptions import DuplicateProductException
            raise DuplicateProductException(code, version)

        # Create new product
        new_product = ProductDefinition(
            code=code,
            name=name,
            version=version,
            description=description,
            uom=source.uom,
            product_type=source.product_type,
        )
        session.add(new_product)
        await session.flush()

        # Clone BOMs
        bom_rows = await session.execute(
            select(BillOfMaterial).where(
                BillOfMaterial.product_id == source_id,
                BillOfMaterial.is_active.is_(True),
            )
        )
        for src_bom in bom_rows.scalars().all():
            new_bom = BillOfMaterial(
                product_id=new_product.id,
                version=src_bom.version,
                effective_date=src_bom.effective_date,
                expiry_date=src_bom.expiry_date,
            )
            session.add(new_bom)
            await session.flush()

            item_rows = await session.execute(
                select(BOMItem).where(
                    BOMItem.bom_id == src_bom.id,
                    BOMItem.is_active.is_(True),
                )
            )
            for src_item in item_rows.scalars().all():
                new_item = BOMItem(
                    bom_id=new_bom.id,
                    material_code=src_item.material_code,
                    quantity=src_item.quantity,
                    uom=src_item.uom,
                    position=src_item.position,
                )
                session.add(new_item)
            await session.flush()

        # Clone routes (via OperationsDefinitionProductAssignment M2M)
        route_rows = await session.execute(
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == source_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
        )
        for src_route in route_rows.scalars().all():
            new_route = OperationsDefinition(
                name=src_route.name,
                version=src_route.version,
                description=src_route.description,
                is_default=src_route.is_default,
            )
            session.add(new_route)
            await session.flush()
            session.add(
                OperationsDefinitionProductAssignment(
                    route_id=new_route.id, product_id=new_product.id,
                )
            )
            await session.flush()

            # Clone steps, building old_step_id → new_step_id map for transitions
            step_id_map: dict[UUID, UUID] = {}
            step_rows = await session.execute(
                select(ProcessSegment).where(
                    ProcessSegment.route_id == src_route.id,
                    ProcessSegment.is_active.is_(True),
                )
            )
            for src_step in step_rows.scalars().all():
                new_step = ProcessSegment(
                    route_id=new_route.id,
                    sequence=src_step.sequence,
                    name=src_step.name,
                    step_type=src_step.step_type,
                    expected_cycle_time_sec=src_step.expected_cycle_time_sec,
                    erp_operation_number=src_step.erp_operation_number,
                    is_initial_step=src_step.is_initial_step,
                )
                session.add(new_step)
                await session.flush()
                step_id_map[src_step.id] = new_step.id

                # Clone step parameters
                param_rows = await session.execute(
                    select(SegmentParameter).where(
                        SegmentParameter.step_id == src_step.id,
                        SegmentParameter.is_active.is_(True),
                    )
                )
                for src_param in param_rows.scalars().all():
                    new_param = SegmentParameter(
                        step_id=new_step.id,
                        name=src_param.name,
                        data_type=src_param.data_type,
                        uom=src_param.uom,
                        target_value=src_param.target_value,
                        lower_limit=src_param.lower_limit,
                        upper_limit=src_param.upper_limit,
                        is_required=src_param.is_required,
                    )
                    session.add(new_param)

                # Clone input/output disposition lists. Dispositions are
                # global rows, so we just re-attach the same Disposition
                # ids to the cloned step.
                in_rows = await session.execute(
                    select(ProcessSegmentInputDisposition).where(
                        ProcessSegmentInputDisposition.step_id == src_step.id,
                        ProcessSegmentInputDisposition.is_active.is_(True),
                    )
                )
                for r in in_rows.scalars().all():
                    session.add(ProcessSegmentInputDisposition(
                        step_id=new_step.id,
                        disposition_id=r.disposition_id,
                        position=r.position,
                    ))
                out_rows = await session.execute(
                    select(ProcessSegmentOutputDisposition).where(
                        ProcessSegmentOutputDisposition.step_id == src_step.id,
                        ProcessSegmentOutputDisposition.is_active.is_(True),
                    )
                )
                for r in out_rows.scalars().all():
                    session.add(ProcessSegmentOutputDisposition(
                        step_id=new_step.id,
                        disposition_id=r.disposition_id,
                        position=r.position,
                    ))
                await session.flush()

        await event_bus.publish(
            product_created(str(new_product.id), new_product.code, new_product.version)
        )
        logger.info(
            "Cloned product %s → %s (code=%s v=%s)",
            source_id, new_product.id, new_product.code, new_product.version,
        )
        return new_product

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

    @staticmethod
    async def delete_bom(session: AsyncSession, bom_id: UUID) -> None:
        """Soft-delete a BOM."""
        bom = await ProductDefService.get_bom(session, bom_id)
        bom.is_active = False
        await session.flush()
        logger.info("Soft-deleted BOM %s", bom_id)

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
    async def list_bom_items_for_step(
        session: AsyncSession,
        step_id: UUID,
    ) -> Sequence[BOMItem]:
        """Return BOM items linked to a specific route step."""
        stmt = (
            select(BOMItem)
            .where(BOMItem.process_segment_id == step_id, BOMItem.is_active.is_(True))
            .order_by(BOMItem.position)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

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

    @staticmethod
    async def get_bom_item(session: AsyncSession, item_id: UUID) -> BOMItem:
        """Get a BOM item by ID."""
        stmt = select(BOMItem).where(
            BOMItem.id == item_id,
            BOMItem.is_active.is_(True),
        )
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException(resource="BOMItem", resource_id=str(item_id))
        return item

    @staticmethod
    async def update_bom_item(
        session: AsyncSession, item_id: UUID, **kwargs: Any
    ) -> BOMItem:
        """Update a BOM item. Accepts process_segment_id=None to clear the link."""
        item = await ProductDefService.get_bom_item(session, item_id)
        # process_segment_id must allow explicit None (unassign from step)
        clearable = {"process_segment_id"}
        for key, value in kwargs.items():
            if value is None and key not in clearable:
                continue
            setattr(item, key, value)
        await session.flush()
        return item

    @staticmethod
    async def delete_bom_item(session: AsyncSession, item_id: UUID) -> None:
        """Soft-delete a BOM item."""
        item = await ProductDefService.get_bom_item(session, item_id)
        item.is_active = False
        await session.flush()
        logger.info("Deleted BOM item %s", item_id)

    # ─── OperationsDefinition operations ─────────────────────────────────────

    @staticmethod
    async def list_routes(
        session: AsyncSession,
        product_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[OperationsDefinition], str | None, bool]:
        """List routes assigned to a product (via OperationsDefinitionProductAssignment)."""
        await ProductDefService.get_product(session, product_id)
        stmt = (
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == product_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
        )
        return await paginate_query(session, stmt, OperationsDefinition, params)

    @staticmethod
    async def get_route(session: AsyncSession, route_id: UUID) -> OperationsDefinition:
        """Get a route by ID."""
        stmt = select(OperationsDefinition).where(
            OperationsDefinition.id == route_id,
            OperationsDefinition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        route = result.scalar_one_or_none()
        if route is None:
            raise NotFoundException(resource="OperationsDefinition", resource_id=str(route_id))
        return route

    @staticmethod
    async def create_route(
        session: AsyncSession, product_id: UUID, **kwargs: Any
    ) -> OperationsDefinition:
        """Create a new route and assign it to a product."""
        await ProductDefService.get_product(session, product_id)

        # If marking as default, unset any existing default
        if kwargs.get("is_default"):
            await ProductDefService._unset_default_route(session, product_id)

        route = OperationsDefinition(**kwargs)
        session.add(route)
        await session.flush()
        session.add(
            OperationsDefinitionProductAssignment(
                route_id=route.id, product_id=product_id,
            )
        )
        await session.flush()

        await event_bus.publish(
            route_created(str(route.id), str(product_id), route.name)
        )
        logger.info("Created route %s (%s) for product %s", route.id, route.name, product_id)
        return route

    @staticmethod
    async def update_route(
        session: AsyncSession, route_id: UUID, **kwargs: Any
    ) -> OperationsDefinition:
        """Update a route."""
        route = await ProductDefService.get_route(session, route_id)

        # If setting as default, unset any existing default across all products this
        # route is assigned to.
        if kwargs.get("is_default"):
            assignment_stmt = select(OperationsDefinitionProductAssignment).where(
                OperationsDefinitionProductAssignment.route_id == route.id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
            )
            for a in (await session.execute(assignment_stmt)).scalars().all():
                await ProductDefService._unset_default_route(session, a.product_id)

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
        stmt = (
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == product_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_default.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        current_default = result.scalar_one_or_none()
        if current_default is not None:
            current_default.is_default = False

    @staticmethod
    async def get_route_with_steps(
        session: AsyncSession, route_id: UUID
    ) -> OperationsDefinition:
        """Get a route with its steps eagerly loaded."""
        stmt = (
            select(OperationsDefinition)
            .where(OperationsDefinition.id == route_id, OperationsDefinition.is_active.is_(True))
            .options(selectinload(OperationsDefinition.steps))
        )
        result = await session.execute(stmt)
        route = result.scalar_one_or_none()
        if route is None:
            raise NotFoundException(resource="OperationsDefinition", resource_id=str(route_id))
        return route

    # ─── ProcessSegment operations ────────────────────────────────────────

    @staticmethod
    async def list_steps(
        session: AsyncSession,
        route_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[ProcessSegment], str | None, bool]:
        """List steps within a route, eagerly loading the input and
        output disposition junction rows + their Disposition targets so
        the API serializer can render the disposition chips without
        triggering lazy IO on the async session."""
        await ProductDefService.get_route(session, route_id)
        stmt = (
            select(ProcessSegment)
            .where(
                ProcessSegment.route_id == route_id,
                ProcessSegment.is_active.is_(True),
            )
            .options(
                selectinload(ProcessSegment.input_dispositions).selectinload(
                    ProcessSegmentInputDisposition.disposition,
                ),
                selectinload(ProcessSegment.output_dispositions).selectinload(
                    ProcessSegmentOutputDisposition.disposition,
                ),
            )
        )
        return await paginate_query(session, stmt, ProcessSegment, params)

    @staticmethod
    async def get_step(session: AsyncSession, step_id: UUID) -> ProcessSegment:
        """Get a route step by ID."""
        stmt = select(ProcessSegment).where(
            ProcessSegment.id == step_id,
            ProcessSegment.is_active.is_(True),
        )
        result = await session.execute(stmt)
        step = result.scalar_one_or_none()
        if step is None:
            raise NotFoundException(resource="ProcessSegment", resource_id=str(step_id))
        return step

    @staticmethod
    async def create_step(
        session: AsyncSession, route_id: UUID, **kwargs: Any
    ) -> ProcessSegment:
        """Create a new step within a route."""
        await ProductDefService.get_route(session, route_id)
        step = ProcessSegment(route_id=route_id, **kwargs)
        session.add(step)
        await session.flush()
        logger.info("Created step %s (seq=%s) in route %s", step.id, step.sequence, route_id)
        return step

    @staticmethod
    async def update_step(
        session: AsyncSession, step_id: UUID, **kwargs: Any
    ) -> ProcessSegment:
        """Update a route step."""
        step = await ProductDefService.get_step(session, step_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(step, key, value)
        await session.flush()
        return step

    # ─── SegmentParameter operations ────────────────────────────────────

    @staticmethod
    async def list_segment_parameters(
        session: AsyncSession,
        step_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[SegmentParameter], str | None, bool]:
        """List parameters for a step."""
        await ProductDefService.get_step(session, step_id)
        stmt = select(SegmentParameter).where(
            SegmentParameter.step_id == step_id,
            SegmentParameter.is_active.is_(True),
        )
        return await paginate_query(session, stmt, SegmentParameter, params)

    @staticmethod
    async def create_step_parameter(
        session: AsyncSession, step_id: UUID, **kwargs: Any
    ) -> SegmentParameter:
        """Create a new parameter specification for a step."""
        await ProductDefService.get_step(session, step_id)
        param = SegmentParameter(step_id=step_id, **kwargs)
        session.add(param)
        await session.flush()
        logger.info("Created step parameter %s (%s) for step %s", param.id, param.name, step_id)
        return param

    @staticmethod
    async def get_step_parameter(
        session: AsyncSession, param_id: UUID,
    ) -> SegmentParameter:
        """Get a step parameter by ID."""
        stmt = select(SegmentParameter).where(
            SegmentParameter.id == param_id,
            SegmentParameter.is_active.is_(True),
        )
        result = await session.execute(stmt)
        param = result.scalar_one_or_none()
        if param is None:
            raise NotFoundException(
                resource="SegmentParameter", resource_id=str(param_id),
            )
        return param

    @staticmethod
    async def update_step_parameter(
        session: AsyncSession, param_id: UUID, **kwargs: Any,
    ) -> SegmentParameter:
        """Update a step parameter. `target_value`, `lower_limit`, `upper_limit`,
        and `uom` may be explicitly cleared by passing None."""
        param = await ProductDefService.get_step_parameter(session, param_id)
        clearable = {"uom", "target_value", "lower_limit", "upper_limit"}
        for key, value in kwargs.items():
            if value is None and key not in clearable:
                continue
            setattr(param, key, value)
        await session.flush()
        return param

    @staticmethod
    async def delete_step_parameter(
        session: AsyncSession, param_id: UUID,
    ) -> None:
        """Soft-delete a step parameter."""
        param = await ProductDefService.get_step_parameter(session, param_id)
        param.is_active = False
        await session.flush()
        logger.info("Deleted step parameter %s", param_id)

    # ─── ERP Routing Sync ────────────────────────────────────────────

    @staticmethod
    async def sync_routes_from_erp(
        session: AsyncSession,
        route_dtos: list[Any],
    ) -> list[OperationsDefinition]:
        """
        Import ERP routing DTOs into the MES database.

        For each ProcessRouteDTO:
        1. Resolve product by code → ProductDefinition
        2. Upsert OperationsDefinition (match on product assignment + name + version)
        3. Upsert ProcessSegments (match on route_id + sequence)

        Returns the list of persisted OperationsDefinition objects.
        """
        persisted: list[OperationsDefinition] = []

        for dto in route_dtos:
            # Resolve product by code
            product_result = await session.execute(
                select(ProductDefinition).where(
                    ProductDefinition.code == dto.product_code,
                    ProductDefinition.is_active.is_(True),
                )
            )
            product = product_result.scalar_one_or_none()
            if product is None:
                logger.warning(
                    "Skipping routing sync: product code '%s' not found in MES",
                    dto.product_code,
                )
                continue

            # Upsert OperationsDefinition (match on product assignment + name + version)
            route_result = await session.execute(
                select(OperationsDefinition)
                .join(
                    OperationsDefinitionProductAssignment,
                    OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
                )
                .where(
                    OperationsDefinitionProductAssignment.product_id == product.id,
                    OperationsDefinitionProductAssignment.is_active.is_(True),
                    OperationsDefinition.name == dto.name,
                    OperationsDefinition.version == dto.version,
                )
            )
            route = route_result.scalar_one_or_none()

            if route is None:
                # Check if this should be default (first route for this product)
                existing_routes = await session.execute(
                    select(OperationsDefinition)
                    .join(
                        OperationsDefinitionProductAssignment,
                        OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
                    )
                    .where(
                        OperationsDefinitionProductAssignment.product_id == product.id,
                        OperationsDefinitionProductAssignment.is_active.is_(True),
                        OperationsDefinition.is_active.is_(True),
                    )
                )
                is_first = existing_routes.scalar_one_or_none() is None

                route = OperationsDefinition(
                    name=dto.name,
                    version=dto.version,
                    description=f"Imported from ERP",
                    is_default=is_first,
                )
                session.add(route)
                await session.flush()
                session.add(
                    OperationsDefinitionProductAssignment(
                        route_id=route.id, product_id=product.id,
                    )
                )
                await session.flush()

                await event_bus.publish(
                    route_created(str(route.id), str(product.id), route.name)
                )
                logger.info(
                    "Created route '%s' v%s for product %s from ERP sync",
                    route.name, route.version, product.code,
                )
            else:
                logger.info(
                    "Route '%s' v%s already exists for product %s — updating steps",
                    route.name, route.version, product.code,
                )

            # Upsert RouteSteps
            for step_dto in dto.steps:
                step_result = await session.execute(
                    select(ProcessSegment).where(
                        ProcessSegment.route_id == route.id,
                        ProcessSegment.sequence == step_dto.sequence,
                    )
                )
                step = step_result.scalar_one_or_none()

                erp_op = str(step_dto.sequence)

                if step is None:
                    step = ProcessSegment(
                        route_id=route.id,
                        sequence=step_dto.sequence,
                        name=step_dto.name,
                        step_type=step_dto.step_type,
                        erp_operation_number=erp_op,
                    )
                    session.add(step)
                else:
                    step.name = step_dto.name
                    step.step_type = step_dto.step_type
                    step.erp_operation_number = erp_op

                if step_dto.work_center_code:
                    # Work-center → equipment-class resolution is handled by the
                    # dispatch layer via SegmentEquipmentRequirement; not stored
                    # directly on the segment anymore.
                    pass

            await session.flush()
            persisted.append(route)

        return persisted

    # ─── Disposition operations ─────────────────────────────────────

    @staticmethod
    async def list_dispositions(
        session: AsyncSession,
        params: PaginationParams,
        *,
        category: str | None = None,
    ) -> tuple[Sequence[Disposition], str | None, bool]:
        """List active dispositions, optionally filtered by category."""
        stmt = select(Disposition).where(Disposition.is_active.is_(True))
        if category is not None:
            stmt = stmt.where(Disposition.category == category)
        return await paginate_query(session, stmt, Disposition, params)

    @staticmethod
    async def get_disposition(session: AsyncSession, disposition_id: UUID) -> Disposition:
        """Get a disposition by ID."""
        stmt = select(Disposition).where(
            Disposition.id == disposition_id,
            Disposition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        disposition = result.scalar_one_or_none()
        if disposition is None:
            raise NotFoundException(resource="Disposition", resource_id=str(disposition_id))
        return disposition

    @staticmethod
    async def create_disposition(session: AsyncSession, **kwargs: Any) -> Disposition:
        """Create a new disposition."""
        disposition = Disposition(**kwargs)
        session.add(disposition)
        await session.flush()
        logger.info("Created disposition %s (code=%s)", disposition.id, disposition.code)
        return disposition

    @staticmethod
    async def update_disposition(
        session: AsyncSession, disposition_id: UUID, **kwargs: Any,
    ) -> Disposition:
        """Update a disposition."""
        disposition = await ProductDefService.get_disposition(session, disposition_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(disposition, key, value)
        await session.flush()
        return disposition

    @staticmethod
    async def delete_disposition(
        session: AsyncSession, disposition_id: UUID,
    ) -> None:
        """Soft-delete a disposition."""
        disposition = await ProductDefService.get_disposition(session, disposition_id)
        disposition.is_active = False
        await session.flush()
        logger.info("Deleted disposition %s", disposition_id)

    # ─── ProcessSegment input/output disposition list operations ──────
    #
    # Disposition lists are managed as full replacements: callers pass
    # the new set of disposition ids and the helpers diff against the
    # existing rows. Cross-step uniqueness of input dispositions is a
    # *route-level* property checked by RoutingEngineService.validate_route
    # before a route is activated; it is intentionally not enforced on
    # individual edits so the editor can build intermediate states.

    @staticmethod
    async def set_step_input_dispositions(
        session: AsyncSession,
        step_id: UUID,
        disposition_ids: list[UUID],
    ) -> list[ProcessSegmentInputDisposition]:
        """Replace the step's input disposition list.

        Cross-step input-uniqueness is **not** enforced here so that the
        editor can freely build intermediate states (loops, rework
        branches, multi-source convergence). The route-level integrity
        check (`RoutingEngineService.validate_route`) flags any
        ambiguous input wiring before the route is put into production.
        """
        await ProductDefService.get_step(session, step_id)
        # Hard-delete prior rows: the (step_id, disposition_id) unique
        # constraint applies to inactive rows too, so soft-delete would
        # block re-adding the same disposition.
        await session.execute(
            delete(ProcessSegmentInputDisposition).where(
                ProcessSegmentInputDisposition.step_id == step_id,
            )
        )
        await session.flush()
        new_rows: list[ProcessSegmentInputDisposition] = []
        for pos, did in enumerate(disposition_ids):
            row = ProcessSegmentInputDisposition(
                step_id=step_id, disposition_id=did, position=pos,
            )
            session.add(row)
            new_rows.append(row)
        await session.flush()
        return new_rows

    @staticmethod
    async def set_step_output_dispositions(
        session: AsyncSession,
        step_id: UUID,
        disposition_ids: list[UUID],
    ) -> list[ProcessSegmentOutputDisposition]:
        """Replace the step's output disposition list.

        Output sharing across steps is allowed by design (it enables
        loops and shared sinks); no cross-step uniqueness check runs.
        """
        await ProductDefService.get_step(session, step_id)
        await session.execute(
            delete(ProcessSegmentOutputDisposition).where(
                ProcessSegmentOutputDisposition.step_id == step_id,
            )
        )
        await session.flush()
        new_rows: list[ProcessSegmentOutputDisposition] = []
        for pos, did in enumerate(disposition_ids):
            row = ProcessSegmentOutputDisposition(
                step_id=step_id, disposition_id=did, position=pos,
            )
            session.add(row)
            new_rows.append(row)
        await session.flush()
        return new_rows

    @staticmethod
    async def get_step_with_dispositions(
        session: AsyncSession, step_id: UUID,
    ) -> ProcessSegment:
        """Fetch a step with input/output disposition lists eagerly loaded."""
        stmt = (
            select(ProcessSegment)
            .where(
                ProcessSegment.id == step_id,
                ProcessSegment.is_active.is_(True),
            )
            .options(
                selectinload(ProcessSegment.input_dispositions).selectinload(
                    ProcessSegmentInputDisposition.disposition,
                ),
                selectinload(ProcessSegment.output_dispositions).selectinload(
                    ProcessSegmentOutputDisposition.disposition,
                ),
            )
        )
        result = await session.execute(stmt)
        step = result.scalar_one_or_none()
        if step is None:
            raise NotFoundException(resource="ProcessSegment", resource_id=str(step_id))
        return step

    # ─── Standalone Route operations (route editor) ──────────────────

    @staticmethod
    async def list_all_routes(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[OperationsDefinition], str | None, bool]:
        """List all active routes (not scoped to a product)."""
        stmt = select(OperationsDefinition).where(OperationsDefinition.is_active.is_(True))
        return await paginate_query(session, stmt, OperationsDefinition, params)

    @staticmethod
    async def create_standalone_route(
        session: AsyncSession, **kwargs: Any,
    ) -> OperationsDefinition:
        """Create a route that is not bound to a single product."""
        route = OperationsDefinition(**kwargs)
        session.add(route)
        await session.flush()
        logger.info("Created standalone route %s (%s)", route.id, route.name)
        return route

    # ─── OperationsDefinitionProductAssignment operations ───────────────────────────

    @staticmethod
    async def list_route_products(
        session: AsyncSession,
        route_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[OperationsDefinitionProductAssignment], str | None, bool]:
        """List product assignments for a route."""
        await ProductDefService.get_route(session, route_id)
        stmt = select(OperationsDefinitionProductAssignment).where(
            OperationsDefinitionProductAssignment.route_id == route_id,
            OperationsDefinitionProductAssignment.is_active.is_(True),
        )
        return await paginate_query(session, stmt, OperationsDefinitionProductAssignment, params)

    @staticmethod
    async def assign_product_to_route(
        session: AsyncSession, route_id: UUID, product_id: UUID,
    ) -> OperationsDefinitionProductAssignment:
        """Assign a product to a route (many-to-many)."""
        await ProductDefService.get_route(session, route_id)
        await ProductDefService.get_product(session, product_id)

        # Check for existing assignment (including soft-deleted)
        stmt = select(OperationsDefinitionProductAssignment).where(
            OperationsDefinitionProductAssignment.route_id == route_id,
            OperationsDefinitionProductAssignment.product_id == product_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            if existing.is_active:
                raise ValueError(
                    f"Product {product_id} is already assigned to route {route_id}"
                )
            # Re-activate soft-deleted assignment
            existing.is_active = True
            await session.flush()
            return existing

        assignment = OperationsDefinitionProductAssignment(route_id=route_id, product_id=product_id)
        session.add(assignment)
        await session.flush()
        logger.info("Assigned product %s to route %s", product_id, route_id)
        return assignment

    @staticmethod
    async def unassign_product_from_route(
        session: AsyncSession, route_id: UUID, product_id: UUID,
    ) -> None:
        """Remove a product assignment from a route (soft-delete)."""
        stmt = select(OperationsDefinitionProductAssignment).where(
            OperationsDefinitionProductAssignment.route_id == route_id,
            OperationsDefinitionProductAssignment.product_id == product_id,
            OperationsDefinitionProductAssignment.is_active.is_(True),
        )
        result = await session.execute(stmt)
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise NotFoundException(
                resource="OperationsDefinitionProductAssignment",
                resource_id=f"route={route_id}, product={product_id}",
            )
        assignment.is_active = False
        await session.flush()
        logger.info("Unassigned product %s from route %s", product_id, route_id)

    # ─── Standalone Route delete / Step delete ────────────────────────

    @staticmethod
    async def delete_standalone_route(
        session: AsyncSession, route_id: UUID,
    ) -> None:
        """Soft-delete a standalone route."""
        route = await ProductDefService.get_route(session, route_id)
        route.is_active = False
        await session.flush()
        logger.info("Deleted standalone route %s", route_id)

    @staticmethod
    async def delete_step(
        session: AsyncSession, step_id: UUID,
    ) -> None:
        """Soft-delete a route step."""
        step = await ProductDefService.get_step(session, step_id)
        step.is_active = False
        await session.flush()
        logger.info("Deleted step %s", step_id)

    # ─── OperationsDefinitionMaterialAssignment operations ──────────────────────────

    @staticmethod
    async def list_route_materials(
        session: AsyncSession,
        route_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[OperationsDefinitionMaterialAssignment], str | None, bool]:
        """List material assignments for a route."""
        await ProductDefService.get_route(session, route_id)
        stmt = select(OperationsDefinitionMaterialAssignment).where(
            OperationsDefinitionMaterialAssignment.route_id == route_id,
            OperationsDefinitionMaterialAssignment.is_active.is_(True),
        )
        return await paginate_query(session, stmt, OperationsDefinitionMaterialAssignment, params)

    @staticmethod
    async def assign_material_to_route(
        session: AsyncSession, route_id: UUID, material_id: UUID,
    ) -> OperationsDefinitionMaterialAssignment:
        """Assign a material to a route (many-to-many)."""
        from mes.core.material.service import MaterialService

        await ProductDefService.get_route(session, route_id)
        await MaterialService.get_material(session, material_id)

        # Check for existing assignment (including soft-deleted)
        stmt = select(OperationsDefinitionMaterialAssignment).where(
            OperationsDefinitionMaterialAssignment.route_id == route_id,
            OperationsDefinitionMaterialAssignment.material_id == material_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            if existing.is_active:
                raise ValueError(
                    f"Material {material_id} is already assigned to route {route_id}"
                )
            # Re-activate soft-deleted assignment
            existing.is_active = True
            await session.flush()
            return existing

        assignment = OperationsDefinitionMaterialAssignment(route_id=route_id, material_id=material_id)
        session.add(assignment)
        await session.flush()
        logger.info("Assigned material %s to route %s", material_id, route_id)
        return assignment

    @staticmethod
    async def unassign_material_from_route(
        session: AsyncSession, route_id: UUID, material_id: UUID,
    ) -> None:
        """Remove a material assignment from a route (soft-delete)."""
        stmt = select(OperationsDefinitionMaterialAssignment).where(
            OperationsDefinitionMaterialAssignment.route_id == route_id,
            OperationsDefinitionMaterialAssignment.material_id == material_id,
            OperationsDefinitionMaterialAssignment.is_active.is_(True),
        )
        result = await session.execute(stmt)
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise NotFoundException(
                resource="OperationsDefinitionMaterialAssignment",
                resource_id=f"route={route_id}, material={material_id}",
            )
        assignment.is_active = False
        await session.flush()
        logger.info("Unassigned material %s from route %s", material_id, route_id)

    # ─── Step Equipment Requirements (ISA-95 Process Segment) ────────

    @staticmethod
    async def list_segment_equipment_requirements(
        session: AsyncSession, step_id: UUID,
    ) -> Sequence[SegmentEquipmentRequirement]:
        """List active equipment requirements for a route step."""
        stmt = select(SegmentEquipmentRequirement).where(
            SegmentEquipmentRequirement.step_id == step_id,
            SegmentEquipmentRequirement.is_active.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_step_equipment_requirement(
        session: AsyncSession, step_id: UUID, **kwargs: Any,
    ) -> SegmentEquipmentRequirement:
        """Add an equipment requirement to a route step."""
        req = SegmentEquipmentRequirement(step_id=step_id, **kwargs)
        session.add(req)
        await session.flush()
        logger.info("Created equipment requirement %s for step %s", req.id, step_id)
        return req

    @staticmethod
    async def update_step_equipment_requirement(
        session: AsyncSession, requirement_id: UUID, **kwargs: Any,
    ) -> SegmentEquipmentRequirement:
        """Update an equipment requirement."""
        stmt = select(SegmentEquipmentRequirement).where(
            SegmentEquipmentRequirement.id == requirement_id,
            SegmentEquipmentRequirement.is_active.is_(True),
        )
        result = await session.execute(stmt)
        req = result.scalar_one_or_none()
        if req is None:
            raise NotFoundException(resource="SegmentEquipmentRequirement", resource_id=str(requirement_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(req, key, value)
        await session.flush()
        return req

    @staticmethod
    async def delete_step_equipment_requirement(
        session: AsyncSession, requirement_id: UUID,
    ) -> None:
        """Soft-delete an equipment requirement."""
        stmt = select(SegmentEquipmentRequirement).where(
            SegmentEquipmentRequirement.id == requirement_id,
            SegmentEquipmentRequirement.is_active.is_(True),
        )
        result = await session.execute(stmt)
        req = result.scalar_one_or_none()
        if req is None:
            raise NotFoundException(resource="SegmentEquipmentRequirement", resource_id=str(requirement_id))
        req.is_active = False
        await session.flush()
        logger.info("Deleted equipment requirement %s", requirement_id)

    # ─── Step Material Requirements (ISA-95 Process Segment) ─────────

    @staticmethod
    async def list_segment_material_requirements(
        session: AsyncSession, step_id: UUID,
    ) -> Sequence[SegmentMaterialRequirement]:
        """List active material requirements for a route step."""
        stmt = select(SegmentMaterialRequirement).where(
            SegmentMaterialRequirement.step_id == step_id,
            SegmentMaterialRequirement.is_active.is_(True),
        ).order_by(SegmentMaterialRequirement.position)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_step_material_requirement(
        session: AsyncSession, step_id: UUID, **kwargs: Any,
    ) -> SegmentMaterialRequirement:
        """Add a material requirement to a route step."""
        req = SegmentMaterialRequirement(step_id=step_id, **kwargs)
        session.add(req)
        await session.flush()
        logger.info("Created material requirement %s for step %s", req.id, step_id)
        return req

    @staticmethod
    async def update_step_material_requirement(
        session: AsyncSession, requirement_id: UUID, **kwargs: Any,
    ) -> SegmentMaterialRequirement:
        """Update a material requirement."""
        stmt = select(SegmentMaterialRequirement).where(
            SegmentMaterialRequirement.id == requirement_id,
            SegmentMaterialRequirement.is_active.is_(True),
        )
        result = await session.execute(stmt)
        req = result.scalar_one_or_none()
        if req is None:
            raise NotFoundException(resource="SegmentMaterialRequirement", resource_id=str(requirement_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(req, key, value)
        await session.flush()
        return req

    @staticmethod
    async def delete_step_material_requirement(
        session: AsyncSession, requirement_id: UUID,
    ) -> None:
        """Soft-delete a material requirement."""
        stmt = select(SegmentMaterialRequirement).where(
            SegmentMaterialRequirement.id == requirement_id,
            SegmentMaterialRequirement.is_active.is_(True),
        )
        result = await session.execute(stmt)
        req = result.scalar_one_or_none()
        if req is None:
            raise NotFoundException(resource="SegmentMaterialRequirement", resource_id=str(requirement_id))
        req.is_active = False
        await session.flush()
        logger.info("Deleted material requirement %s", requirement_id)
