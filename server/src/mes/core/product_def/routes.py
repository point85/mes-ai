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

from fastapi import APIRouter, Depends, Query
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
    BOMItemUpdate,
    BOMRead,
    BOMUpdate,
    DispositionCreate,
    DispositionRead,
    DispositionUpdate,
    ProductClone,
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
    StepParameterUpdate,
    RouteProductAssignmentCreate,
    RouteProductAssignmentRead,
    RouteMaterialAssignmentCreate,
    RouteMaterialAssignmentRead,
    StepEquipmentRequirementCreate,
    StepEquipmentRequirementRead,
    StepEquipmentRequirementUpdate,
    StepMaterialRequirementCreate,
    StepMaterialRequirementRead,
    StepMaterialRequirementUpdate,
)
from .service import ProductDefService

router = APIRouter(prefix="/api/v1", tags=["Product Definition"])
svc = ProductDefService


# ─── Dispositions ─────────────────────────────────────────────────────


@router.get("/dispositions")
async def list_dispositions(
    category: str | None = Query(
        None,
        description="Optional filter: 'route', 'hold', or 'scrap'.",
    ),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List all active dispositions, optionally filtered by category."""
    items, cursor, has_more = await svc.list_dispositions(
        session, params, category=category,
    )
    return list_response(
        [DispositionRead.model_validate(d).model_dump() for d in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/dispositions", status_code=201)
async def create_disposition(
    body: DispositionCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a new disposition."""
    disposition = await svc.create_disposition(session, **body.model_dump())
    await session.commit()
    return success_response(DispositionRead.model_validate(disposition).model_dump())


@router.get("/dispositions/{disposition_id}")
async def get_disposition(
    disposition_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a disposition by ID."""
    disposition = await svc.get_disposition(session, disposition_id)
    return success_response(DispositionRead.model_validate(disposition).model_dump())


@router.put("/dispositions/{disposition_id}")
async def update_disposition(
    disposition_id: UUID,
    body: DispositionUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a disposition."""
    disposition = await svc.update_disposition(
        session, disposition_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(DispositionRead.model_validate(disposition).model_dump())


@router.delete("/dispositions/{disposition_id}", status_code=204)
async def delete_disposition(
    disposition_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a disposition."""
    await svc.delete_disposition(session, disposition_id)
    await session.commit()


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


@router.post("/products/{product_id}/clone", status_code=201)
async def clone_product(
    product_id: UUID,
    body: ProductClone,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Deep-clone a product with its BOMs and routes."""
    product = await svc.clone_product(session, product_id, **body.model_dump())
    await session.commit()
    return success_response(ProductRead.model_validate(product).model_dump())


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


@router.delete("/boms/{bom_id}", status_code=204)
async def delete_bom(
    bom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a BOM."""
    await svc.delete_bom(session, bom_id)
    await session.commit()


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


@router.get("/bom-items/{item_id}")
async def get_bom_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a BOM item by ID."""
    item = await svc.get_bom_item(session, item_id)
    return success_response(BOMItemRead.model_validate(item).model_dump())


@router.put("/bom-items/{item_id}")
async def update_bom_item(
    item_id: UUID,
    body: BOMItemUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a BOM item."""
    item = await svc.update_bom_item(
        session, item_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(BOMItemRead.model_validate(item).model_dump())


@router.delete("/bom-items/{item_id}", status_code=204)
async def delete_bom_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a BOM item."""
    await svc.delete_bom_item(session, item_id)
    await session.commit()


@router.get("/process-segments/{step_id}/bom-items")
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


@router.get("/products/{product_id}/operations-definitions")
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


@router.post("/products/{product_id}/operations-definitions", status_code=201)
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


@router.get("/operations-definitions/{route_id}")
async def get_route(
    route_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a route by ID."""
    route = await svc.get_route(session, route_id)
    return success_response(RouteRead.model_validate(route).model_dump())


@router.put("/operations-definitions/{route_id}")
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


@router.post("/operations-definitions/{route_id}/validate")
async def validate_route_endpoint(
    route_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Run route-integrity validation against the saved route.

    Read-only — performs no edits. Returns
    ``{"valid": bool, "errors": [str], "warnings": [str], "stats": {...}}``
    so the UI can show whether the route is ready to be saved/used.
    """
    from mes.core.routing.service import RoutingEngineService

    result = await RoutingEngineService.validate_route(session, route_id)
    return success_response(result)


# ─── Route Steps ──────────────────────────────────────────────────────


@router.get("/operations-definitions/{route_id}/process-segments")
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


@router.post("/operations-definitions/{route_id}/process-segments", status_code=201)
async def create_step(
    route_id: UUID,
    body: RouteStepCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Create a step within a route.

    Body may include `input_disposition_ids` and `output_disposition_ids`
    to set the step's input/output disposition lists in the same call.
    The route graph is fully derived from these lists.
    """
    payload = body.model_dump()
    in_ids = payload.pop("input_disposition_ids", []) or []
    out_ids = payload.pop("output_disposition_ids", []) or []
    step = await svc.create_step(session, route_id, **payload)
    if in_ids:
        await svc.set_step_input_dispositions(session, step.id, in_ids)
    if out_ids:
        await svc.set_step_output_dispositions(session, step.id, out_ids)
    step = await svc.get_step_with_dispositions(session, step.id)
    await session.commit()
    return success_response(_step_to_read_dict(step))


@router.get("/process-segments/{step_id}")
async def get_step(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a route step by ID (with input/output disposition lists)."""
    step = await svc.get_step_with_dispositions(session, step_id)
    return success_response(_step_to_read_dict(step))


@router.put("/process-segments/{step_id}")
async def update_step(
    step_id: UUID,
    body: RouteStepUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a route step.

    `input_disposition_ids` / `output_disposition_ids` (when provided)
    fully replace the step's input/output disposition lists; omit them
    to leave the existing lists untouched.
    """
    payload = body.model_dump(exclude_unset=True)
    in_ids = payload.pop("input_disposition_ids", None)
    out_ids = payload.pop("output_disposition_ids", None)
    step = await svc.update_step(session, step_id, **payload)
    if in_ids is not None:
        await svc.set_step_input_dispositions(session, step.id, in_ids)
    if out_ids is not None:
        await svc.set_step_output_dispositions(session, step.id, out_ids)
    step = await svc.get_step_with_dispositions(session, step.id)
    await session.commit()
    return success_response(_step_to_read_dict(step))


def _step_to_read_dict(step) -> dict:
    """Build a RouteStepRead-shaped dict from a ProcessSegment + its
    input/output disposition junction rows. We hand-build because the
    Read schema's `input_dispositions`/`output_dispositions` fields are
    Disposition rows, not the junction rows."""
    return {
        "id": step.id,
        "route_id": step.route_id,
        "sequence": step.sequence,
        "name": step.name,
        "step_type": step.step_type,
        "equipment_class_id": step.equipment_class_id,
        "expected_cycle_time_sec": step.expected_cycle_time_sec,
        "erp_operation_number": step.erp_operation_number,
        "is_initial_step": step.is_initial_step,
        "input_dispositions": [
            DispositionRead.model_validate(r.disposition).model_dump()
            for r in step.input_dispositions
            if r.is_active
        ],
        "output_dispositions": [
            DispositionRead.model_validate(r.disposition).model_dump()
            for r in step.output_dispositions
            if r.is_active
        ],
        "is_active": step.is_active,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
    }


# ─── Step Parameters ──────────────────────────────────────────────────


@router.get("/process-segments/{step_id}/parameters")
async def list_segment_parameters(
    step_id: UUID,
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List parameters for a step."""
    items, cursor, has_more = await svc.list_segment_parameters(session, step_id, params)
    return list_response(
        [StepParameterRead.model_validate(p).model_dump() for p in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/process-segments/{step_id}/parameters", status_code=201)
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


@router.get("/segment-parameters/{param_id}")
async def get_step_parameter(
    param_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """Get a step parameter by ID."""
    param = await svc.get_step_parameter(session, param_id)
    return success_response(StepParameterRead.model_validate(param).model_dump())


@router.put("/segment-parameters/{param_id}")
async def update_step_parameter(
    param_id: UUID,
    body: StepParameterUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a step parameter."""
    param = await svc.update_step_parameter(
        session, param_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(StepParameterRead.model_validate(param).model_dump())


@router.delete("/segment-parameters/{param_id}", status_code=204)
async def delete_step_parameter(
    param_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Delete a step parameter."""
    await svc.delete_step_parameter(session, param_id)
    await session.commit()


# ─── Standalone Routes (Route Editor) ────────────────────────────────


@router.get("/operations-definitions")
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


@router.post("/operations-definitions", status_code=201)
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


@router.get("/operations-definitions/{route_id}/products")
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


@router.post("/operations-definitions/{route_id}/products", status_code=201)
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


@router.delete("/operations-definitions/{route_id}/products/{product_id}", status_code=204)
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


@router.delete("/operations-definitions/{route_id}", status_code=204)
async def delete_standalone_route(
    route_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a standalone route."""
    await svc.delete_standalone_route(session, route_id)
    await session.commit()


@router.delete("/process-segments/{step_id}", status_code=204)
async def delete_step(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Soft-delete a route step."""
    await svc.delete_step(session, step_id)
    await session.commit()


# ─── Route–Material Assignments ──────────────────────────────────────


@router.get("/operations-definitions/{route_id}/materials")
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


@router.post("/operations-definitions/{route_id}/materials", status_code=201)
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


@router.delete("/operations-definitions/{route_id}/materials/{material_id}", status_code=204)
async def unassign_material_from_route(
    route_id: UUID,
    material_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Remove a material assignment from a route."""
    await svc.unassign_material_from_route(session, route_id, material_id)
    await session.commit()


# ── Step Equipment Requirements (ISA-95 Process Segment) ────────────


@router.get("/process-segments/{step_id}/equipment-requirements")
async def list_segment_equipment_requirements(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List equipment requirements for a route step."""
    items = await svc.list_segment_equipment_requirements(session, step_id)
    return list_response(
        [StepEquipmentRequirementRead.model_validate(r).model_dump() for r in items],
    )


@router.post("/process-segments/{step_id}/equipment-requirements", status_code=201)
async def create_step_equipment_requirement(
    step_id: UUID,
    body: StepEquipmentRequirementCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Add an equipment requirement to a route step."""
    req = await svc.create_step_equipment_requirement(
        session, step_id, **body.model_dump(),
    )
    await session.commit()
    return success_response(
        StepEquipmentRequirementRead.model_validate(req).model_dump(),
    )


@router.patch("/segment-equipment-requirements/{requirement_id}")
async def update_step_equipment_requirement(
    requirement_id: UUID,
    body: StepEquipmentRequirementUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update an equipment requirement."""
    req = await svc.update_step_equipment_requirement(
        session, requirement_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(
        StepEquipmentRequirementRead.model_validate(req).model_dump(),
    )


@router.delete("/segment-equipment-requirements/{requirement_id}", status_code=204)
async def delete_step_equipment_requirement(
    requirement_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Remove an equipment requirement from a step."""
    await svc.delete_step_equipment_requirement(session, requirement_id)
    await session.commit()


# ── Step Material Requirements (ISA-95 Process Segment) ─────────────


@router.get("/process-segments/{step_id}/material-requirements")
async def list_segment_material_requirements(
    step_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.read")),
):
    """List material requirements for a route step."""
    items = await svc.list_segment_material_requirements(session, step_id)
    return list_response(
        [StepMaterialRequirementRead.model_validate(r).model_dump() for r in items],
    )


@router.post("/process-segments/{step_id}/material-requirements", status_code=201)
async def create_step_material_requirement(
    step_id: UUID,
    body: StepMaterialRequirementCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.create")),
):
    """Add a material requirement to a route step."""
    req = await svc.create_step_material_requirement(
        session, step_id, **body.model_dump(),
    )
    await session.commit()
    return success_response(
        StepMaterialRequirementRead.model_validate(req).model_dump(),
    )


@router.patch("/segment-material-requirements/{requirement_id}")
async def update_step_material_requirement(
    requirement_id: UUID,
    body: StepMaterialRequirementUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.update")),
):
    """Update a material requirement."""
    req = await svc.update_step_material_requirement(
        session, requirement_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(
        StepMaterialRequirementRead.model_validate(req).model_dump(),
    )


@router.delete("/segment-material-requirements/{requirement_id}", status_code=204)
async def delete_step_material_requirement(
    requirement_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("product_def.delete")),
):
    """Remove a material requirement from a step."""
    await svc.delete_step_material_requirement(session, requirement_id)
    await session.commit()
