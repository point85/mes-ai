"""
PROD-DEF: REST API routes for the product definition domain.

Endpoints per ARCHITECTURE.md §6.3 — Product Definition (PROD-DEF):
- Products:        /api/v1/products
- BOMs:            /api/v1/products/{product_id}/boms, /api/v1/boms/{bom_id}
- BOM Items:       /api/v1/boms/{bom_id}/items
- Routes:          /api/v1/products/{product_id}/routes, /api/v1/routes/{route_id}
- Route Steps:     /api/v1/routes/{route_id}/steps, /api/v1/steps/{step_id}
- Step Parameters: /api/v1/steps/{step_id}/parameters
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.pagination import PaginationParams, get_pagination_params
from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .schemas import (
    BOMCreate,
    BOMItemCreate,
    BOMItemRead,
    BOMRead,
    BOMUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    RouteCreate,
    RouteRead,
    RouteStepCreate,
    RouteStepRead,
    RouteStepUpdate,
    RouteUpdate,
    StepParameterCreate,
    StepParameterRead,
    StepTransitionCreate,
    StepTransitionRead,
    StepTransitionUpdate,
    RouteProductAssignmentCreate,
    RouteProductAssignmentRead,
    RouteMaterialAssignmentCreate,
    RouteMaterialAssignmentRead,
)
from .service import ProductDefService

router = APIRouter(prefix="/api/v1", tags=["Product Definition"])
svc = ProductDefService


# ─── Products ─────────────────────────────────────────────────────────


@router.get("/products")
async def list_products(
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List all active product definitions with pagination."""
    items, cursor, has_more = await svc.list_products(session, params)
    return list_response(
        [ProductRead.model_validate(p).model_dump() for p in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/products", status_code=201)
async def create_product(
    body: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a new product definition."""
    product = await svc.create_product(session, **body.model_dump())
    await session.commit()
    return success_response(ProductRead.model_validate(product).model_dump())


@router.get("/products/{product_id}")
async def get_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a product definition by ID."""
    product = await svc.get_product(session, product_id)
    return success_response(ProductRead.model_validate(product).model_dump())


@router.put("/products/{product_id}")
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a product definition."""
    product = await svc.update_product(
        session, product_id, **body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return success_response(ProductRead.model_validate(product).model_dump())


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a product definition."""
    await svc.delete_product(session, product_id)
    await session.commit()


# ─── BOMs ─────────────────────────────────────────────────────────────


@router.get("/products/{product_id}/boms")
async def list_boms(
    product_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List BOMs for a product."""
    items, cursor, has_more = await svc.list_boms(session, product_id, params)
    return list_response(
        [BOMRead.model_validate(b).model_dump() for b in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/products/{product_id}/boms", status_code=201)
async def create_bom(
    product_id: UUID,
    body: BOMCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a BOM for a product."""
    bom = await svc.create_bom(session, product_id, **body.model_dump())
    await session.commit()
    return success_response(BOMRead.model_validate(bom).model_dump())


@router.get("/boms/{bom_id}")
async def get_bom(
    bom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a BOM by ID."""
    bom = await svc.get_bom(session, bom_id)
    return success_response(BOMRead.model_validate(bom).model_dump())


@router.put("/boms/{bom_id}")
async def update_bom(
    bom_id: UUID,
    body: BOMUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a BOM."""
    bom = await svc.update_bom(session, bom_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(BOMRead.model_validate(bom).model_dump())


# ─── BOM Items ────────────────────────────────────────────────────────


@router.get("/boms/{bom_id}/items")
async def list_bom_items(
    bom_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List items within a BOM."""
    items, cursor, has_more = await svc.list_bom_items(session, bom_id, params)
    return list_response(
        [BOMItemRead.model_validate(i).model_dump() for i in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/boms/{bom_id}/items", status_code=201)
async def create_bom_item(
    bom_id: UUID,
    body: BOMItemCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a BOM item within a BOM."""
    item = await svc.create_bom_item(session, bom_id, **body.model_dump())
    await session.commit()
    return success_response(BOMItemRead.model_validate(item).model_dump())


@router.get("/steps/{step_id}/bom-items")
async def list_step_bom_items(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List BOM items assigned to a specific route step."""
    items = await svc.list_bom_items_for_step(session, step_id)
    return success_response(
        [BOMItemRead.model_validate(i).model_dump() for i in items],
    )


# ─── Routes ───────────────────────────────────────────────────────────


@router.get("/products/{product_id}/routes")
async def list_routes(
    product_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List routes for a product."""
    items, cursor, has_more = await svc.list_routes(session, product_id, params)
    return list_response(
        [RouteRead.model_validate(r).model_dump() for r in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/products/{product_id}/routes", status_code=201)
async def create_route(
    product_id: UUID,
    body: RouteCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a route for a product."""
    route = await svc.create_route(session, product_id, **body.model_dump())
    await session.commit()
    return success_response(RouteRead.model_validate(route).model_dump())


@router.get("/routes/{route_id}")
async def get_route(
    route_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a route by ID."""
    route = await svc.get_route(session, route_id)
    return success_response(RouteRead.model_validate(route).model_dump())


@router.put("/routes/{route_id}")
async def update_route(
    route_id: UUID,
    body: RouteUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a route."""
    route = await svc.update_route(
        session, route_id, **body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return success_response(RouteRead.model_validate(route).model_dump())


# ─── Route Steps ──────────────────────────────────────────────────────


@router.get("/routes/{route_id}/steps")
async def list_steps(
    route_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List steps within a route."""
    items, cursor, has_more = await svc.list_steps(session, route_id, params)
    return list_response(
        [RouteStepRead.model_validate(s).model_dump() for s in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/routes/{route_id}/steps", status_code=201)
async def create_step(
    route_id: UUID,
    body: RouteStepCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a step within a route."""
    step = await svc.create_step(session, route_id, **body.model_dump())
    await session.commit()
    return success_response(RouteStepRead.model_validate(step).model_dump())


@router.get("/steps/{step_id}")
async def get_step(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a route step by ID."""
    step = await svc.get_step(session, step_id)
    return success_response(RouteStepRead.model_validate(step).model_dump())


@router.put("/steps/{step_id}")
async def update_step(
    step_id: UUID,
    body: RouteStepUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a route step."""
    step = await svc.update_step(
        session, step_id, **body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return success_response(RouteStepRead.model_validate(step).model_dump())


# ─── Step Parameters ──────────────────────────────────────────────────


@router.get("/steps/{step_id}/parameters")
async def list_step_parameters(
    step_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List parameters for a step."""
    items, cursor, has_more = await svc.list_step_parameters(session, step_id, params)
    return list_response(
        [StepParameterRead.model_validate(p).model_dump() for p in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/steps/{step_id}/parameters", status_code=201)
async def create_step_parameter(
    step_id: UUID,
    body: StepParameterCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a parameter specification for a step."""
    param = await svc.create_step_parameter(session, step_id, **body.model_dump())
    await session.commit()
    return success_response(StepParameterRead.model_validate(param).model_dump())


# ─── Step Transitions ────────────────────────────────────────────────


@router.get("/steps/{step_id}/transitions")
async def list_step_transitions(
    step_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List outgoing transitions for a step."""
    items, cursor, has_more = await svc.list_step_transitions(session, step_id, params)
    return list_response(
        [StepTransitionRead.model_validate(t).model_dump() for t in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/steps/{step_id}/transitions", status_code=201)
async def create_step_transition(
    step_id: UUID,
    body: StepTransitionCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create an outgoing transition from a step (route graph edge)."""
    transition = await svc.create_step_transition(
        session, step_id, **body.model_dump(),
    )
    await session.commit()
    return success_response(StepTransitionRead.model_validate(transition).model_dump())


@router.get("/transitions/{transition_id}")
async def get_step_transition(
    transition_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a step transition by ID."""
    transition = await svc.get_step_transition(session, transition_id)
    return success_response(StepTransitionRead.model_validate(transition).model_dump())


@router.put("/transitions/{transition_id}")
async def update_step_transition(
    transition_id: UUID,
    body: StepTransitionUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a step transition."""
    transition = await svc.update_step_transition(
        session, transition_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(StepTransitionRead.model_validate(transition).model_dump())


@router.delete("/transitions/{transition_id}", status_code=204)
async def delete_step_transition(
    transition_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Delete a step transition."""
    await svc.delete_step_transition(session, transition_id)
    await session.commit()


# ─── Standalone Routes (Route Editor) ────────────────────────────────


@router.get("/routes")
async def list_all_routes(
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List all routes across all products + standalone routes."""
    items, cursor, has_more = await svc.list_all_routes(session, params)
    return list_response(
        [RouteRead.model_validate(r).model_dump() for r in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/routes", status_code=201)
async def create_standalone_route(
    body: RouteCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a standalone route (not bound to a single product)."""
    route = await svc.create_standalone_route(session, **body.model_dump())
    await session.commit()
    return success_response(RouteRead.model_validate(route).model_dump())


# ─── Route–Product Assignments ───────────────────────────────────────


@router.get("/routes/{route_id}/products")
async def list_route_products(
    route_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List products assigned to a route."""
    items, cursor, has_more = await svc.list_route_products(session, route_id, params)
    return list_response(
        [RouteProductAssignmentRead.model_validate(a).model_dump() for a in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/routes/{route_id}/products", status_code=201)
async def assign_product_to_route(
    route_id: UUID,
    body: RouteProductAssignmentCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Assign a product to a route."""
    assignment = await svc.assign_product_to_route(
        session, route_id, body.product_id,
    )
    await session.commit()
    return success_response(
        RouteProductAssignmentRead.model_validate(assignment).model_dump()
    )


@router.delete("/routes/{route_id}/products/{product_id}", status_code=204)
async def unassign_product_from_route(
    route_id: UUID,
    product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Remove a product assignment from a route."""
    await svc.unassign_product_from_route(session, route_id, product_id)
    await session.commit()


# ─── Standalone Route Delete ─────────────────────────────────────────


@router.delete("/routes/{route_id}", status_code=204)
async def delete_standalone_route(
    route_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a standalone route."""
    await svc.delete_standalone_route(session, route_id)
    await session.commit()


@router.delete("/steps/{step_id}", status_code=204)
async def delete_step(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a route step."""
    await svc.delete_step(session, step_id)
    await session.commit()


# ─── Route–Material Assignments ──────────────────────────────────────


@router.get("/routes/{route_id}/materials")
async def list_route_materials(
    route_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List materials assigned to a route."""
    items, cursor, has_more = await svc.list_route_materials(session, route_id, params)
    return list_response(
        [RouteMaterialAssignmentRead.model_validate(a).model_dump() for a in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/routes/{route_id}/materials", status_code=201)
async def assign_material_to_route(
    route_id: UUID,
    body: RouteMaterialAssignmentCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Assign a material to a route."""
    assignment = await svc.assign_material_to_route(
        session, route_id, body.material_id,
    )
    await session.commit()
    return success_response(
        RouteMaterialAssignmentRead.model_validate(assignment).model_dump()
    )


@router.delete("/routes/{route_id}/materials/{material_id}", status_code=204)
async def unassign_material_from_route(
    route_id: UUID,
    material_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Remove a material assignment from a route."""
    await svc.unassign_material_from_route(session, route_id, material_id)
    await session.commit()
