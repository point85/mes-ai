"""
PROD-DEF: Business logic service for the product definition domain.

Provides CRUD operations for ProductDefinition, BillOfMaterial, BOMItem,
ProcessRoute, RouteStep, StepParameter, StepTransition.
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
    RouteMaterialAssignment,
    RouteProductAssignment,
    RouteStep,
    StepParameter,
    StepTransition,
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
    async def list_bom_items_for_step(
        session: AsyncSession,
        step_id: UUID,
    ) -> Sequence[BOMItem]:
        """Return BOM items linked to a specific route step."""
        stmt = (
            select(BOMItem)
            .where(BOMItem.route_step_id == step_id, BOMItem.is_active.is_(True))
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

    # ─── ERP Routing Sync ────────────────────────────────────────────

    @staticmethod
    async def sync_routes_from_erp(
        session: AsyncSession,
        route_dtos: list[Any],
    ) -> list[ProcessRoute]:
        """
        Import ERP routing DTOs into the MES database.

        For each ProcessRouteDTO:
        1. Resolve product by code → ProductDefinition
        2. Upsert ProcessRoute (match on product_id + name + version)
        3. Upsert RouteSteps (match on route_id + sequence)
        4. Resolve work_center_code → work_cell_id via WorkCell.code

        Returns the list of persisted ProcessRoute objects.
        """
        from mes.core.physical_model.models import WorkCell

        persisted: list[ProcessRoute] = []

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

            # Upsert ProcessRoute
            route_result = await session.execute(
                select(ProcessRoute).where(
                    ProcessRoute.product_id == product.id,
                    ProcessRoute.name == dto.name,
                    ProcessRoute.version == dto.version,
                )
            )
            route = route_result.scalar_one_or_none()

            if route is None:
                # Check if this should be default (first route for this product)
                existing_routes = await session.execute(
                    select(ProcessRoute).where(
                        ProcessRoute.product_id == product.id,
                        ProcessRoute.is_active.is_(True),
                    )
                )
                is_first = existing_routes.scalar_one_or_none() is None

                route = ProcessRoute(
                    product_id=product.id,
                    name=dto.name,
                    version=dto.version,
                    description=f"Imported from ERP",
                    is_default=is_first,
                )
                session.add(route)
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

            # Build work_center_code → work_cell_id lookup
            wc_codes = [
                s.work_center_code for s in dto.steps if s.work_center_code
            ]
            wc_map: dict[str, Any] = {}
            if wc_codes:
                wc_result = await session.execute(
                    select(WorkCell).where(
                        WorkCell.code.in_(wc_codes),
                        WorkCell.is_active.is_(True),
                    )
                )
                for wc in wc_result.scalars().all():
                    wc_map[wc.code] = wc.id

            # Upsert RouteSteps
            for step_dto in dto.steps:
                step_result = await session.execute(
                    select(RouteStep).where(
                        RouteStep.route_id == route.id,
                        RouteStep.sequence == step_dto.sequence,
                    )
                )
                step = step_result.scalar_one_or_none()

                work_cell_id = wc_map.get(step_dto.work_center_code) if step_dto.work_center_code else None
                erp_op = str(step_dto.sequence)

                if step is None:
                    step = RouteStep(
                        route_id=route.id,
                        sequence=step_dto.sequence,
                        name=step_dto.name,
                        step_type=step_dto.step_type,
                        work_cell_id=work_cell_id,
                        erp_operation_number=erp_op,
                    )
                    session.add(step)
                else:
                    step.name = step_dto.name
                    step.step_type = step_dto.step_type
                    step.work_cell_id = work_cell_id
                    step.erp_operation_number = erp_op

                if step_dto.work_center_code and step_dto.work_center_code not in wc_map:
                    logger.warning(
                        "Work center '%s' not found in MES — step %d work_cell_id left null",
                        step_dto.work_center_code, step_dto.sequence,
                    )

            await session.flush()
            persisted.append(route)

        return persisted

    # ─── StepTransition operations ───────────────────────────────────

    @staticmethod
    async def list_step_transitions(
        session: AsyncSession,
        step_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[StepTransition], str | None, bool]:
        """List outgoing transitions for a step."""
        await ProductDefService.get_step(session, step_id)
        stmt = select(StepTransition).where(
            StepTransition.from_step_id == step_id,
            StepTransition.is_active.is_(True),
        )
        return await paginate_query(session, stmt, StepTransition, params)

    @staticmethod
    async def get_step_transition(
        session: AsyncSession, transition_id: UUID,
    ) -> StepTransition:
        """Get a step transition by ID."""
        stmt = select(StepTransition).where(
            StepTransition.id == transition_id,
            StepTransition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        transition = result.scalar_one_or_none()
        if transition is None:
            raise NotFoundException(
                resource="StepTransition", resource_id=str(transition_id),
            )
        return transition

    @staticmethod
    async def create_step_transition(
        session: AsyncSession, from_step_id: UUID, **kwargs: Any,
    ) -> StepTransition:
        """Create a new transition from a step."""
        from_step = await ProductDefService.get_step(session, from_step_id)
        # Validate to_step exists and belongs to the same route
        to_step_id = kwargs["to_step_id"]
        to_step = await ProductDefService.get_step(session, to_step_id)
        if to_step.route_id != from_step.route_id:
            raise ValueError(
                f"to_step {to_step_id} belongs to route {to_step.route_id}, "
                f"but from_step {from_step_id} belongs to route {from_step.route_id}"
            )
        transition = StepTransition(from_step_id=from_step_id, **kwargs)
        session.add(transition)
        await session.flush()
        logger.info(
            "Created transition %s → %s (condition=%s) in route %s",
            from_step_id, to_step_id, transition.condition, from_step.route_id,
        )
        return transition

    @staticmethod
    async def update_step_transition(
        session: AsyncSession, transition_id: UUID, **kwargs: Any,
    ) -> StepTransition:
        """Update a step transition."""
        transition = await ProductDefService.get_step_transition(
            session, transition_id,
        )
        for key, value in kwargs.items():
            if value is not None:
                setattr(transition, key, value)
        await session.flush()
        return transition

    @staticmethod
    async def delete_step_transition(
        session: AsyncSession, transition_id: UUID,
    ) -> None:
        """Soft-delete a step transition."""
        transition = await ProductDefService.get_step_transition(
            session, transition_id,
        )
        transition.is_active = False
        await session.flush()
        logger.info("Deleted transition %s", transition_id)

    # ─── Standalone Route operations (route editor) ──────────────────

    @staticmethod
    async def list_all_routes(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[ProcessRoute], str | None, bool]:
        """List all active routes (not scoped to a product)."""
        stmt = select(ProcessRoute).where(ProcessRoute.is_active.is_(True))
        return await paginate_query(session, stmt, ProcessRoute, params)

    @staticmethod
    async def create_standalone_route(
        session: AsyncSession, **kwargs: Any,
    ) -> ProcessRoute:
        """Create a route that is not bound to a single product."""
        route = ProcessRoute(**kwargs)
        session.add(route)
        await session.flush()
        logger.info("Created standalone route %s (%s)", route.id, route.name)
        return route

    # ─── RouteProductAssignment operations ───────────────────────────

    @staticmethod
    async def list_route_products(
        session: AsyncSession,
        route_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[RouteProductAssignment], str | None, bool]:
        """List product assignments for a route."""
        await ProductDefService.get_route(session, route_id)
        stmt = select(RouteProductAssignment).where(
            RouteProductAssignment.route_id == route_id,
            RouteProductAssignment.is_active.is_(True),
        )
        return await paginate_query(session, stmt, RouteProductAssignment, params)

    @staticmethod
    async def assign_product_to_route(
        session: AsyncSession, route_id: UUID, product_id: UUID,
    ) -> RouteProductAssignment:
        """Assign a product to a route (many-to-many)."""
        await ProductDefService.get_route(session, route_id)
        await ProductDefService.get_product(session, product_id)

        # Check for existing assignment (including soft-deleted)
        stmt = select(RouteProductAssignment).where(
            RouteProductAssignment.route_id == route_id,
            RouteProductAssignment.product_id == product_id,
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

        assignment = RouteProductAssignment(route_id=route_id, product_id=product_id)
        session.add(assignment)
        await session.flush()
        logger.info("Assigned product %s to route %s", product_id, route_id)
        return assignment

    @staticmethod
    async def unassign_product_from_route(
        session: AsyncSession, route_id: UUID, product_id: UUID,
    ) -> None:
        """Remove a product assignment from a route (soft-delete)."""
        stmt = select(RouteProductAssignment).where(
            RouteProductAssignment.route_id == route_id,
            RouteProductAssignment.product_id == product_id,
            RouteProductAssignment.is_active.is_(True),
        )
        result = await session.execute(stmt)
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise NotFoundException(
                resource="RouteProductAssignment",
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

    # ─── RouteMaterialAssignment operations ──────────────────────────

    @staticmethod
    async def list_route_materials(
        session: AsyncSession,
        route_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[RouteMaterialAssignment], str | None, bool]:
        """List material assignments for a route."""
        await ProductDefService.get_route(session, route_id)
        stmt = select(RouteMaterialAssignment).where(
            RouteMaterialAssignment.route_id == route_id,
            RouteMaterialAssignment.is_active.is_(True),
        )
        return await paginate_query(session, stmt, RouteMaterialAssignment, params)

    @staticmethod
    async def assign_material_to_route(
        session: AsyncSession, route_id: UUID, material_id: UUID,
    ) -> RouteMaterialAssignment:
        """Assign a material to a route (many-to-many)."""
        from mes.core.material.service import MaterialService

        await ProductDefService.get_route(session, route_id)
        await MaterialService.get_material(session, material_id)

        # Check for existing assignment (including soft-deleted)
        stmt = select(RouteMaterialAssignment).where(
            RouteMaterialAssignment.route_id == route_id,
            RouteMaterialAssignment.material_id == material_id,
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

        assignment = RouteMaterialAssignment(route_id=route_id, material_id=material_id)
        session.add(assignment)
        await session.flush()
        logger.info("Assigned material %s to route %s", material_id, route_id)
        return assignment

    @staticmethod
    async def unassign_material_from_route(
        session: AsyncSession, route_id: UUID, material_id: UUID,
    ) -> None:
        """Remove a material assignment from a route (soft-delete)."""
        stmt = select(RouteMaterialAssignment).where(
            RouteMaterialAssignment.route_id == route_id,
            RouteMaterialAssignment.material_id == material_id,
            RouteMaterialAssignment.is_active.is_(True),
        )
        result = await session.execute(stmt)
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise NotFoundException(
                resource="RouteMaterialAssignment",
                resource_id=f"route={route_id}, material={material_id}",
            )
        assignment.is_active = False
        await session.flush()
        logger.info("Unassigned material %s from route %s", material_id, route_id)
