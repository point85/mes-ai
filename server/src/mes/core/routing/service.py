"""
ROUTE-ENGINE: Routing engine service for determining step progression.

Provides runtime logic for:
- Resolving the assigned route for a production order
- Resolving the first step in a route (entry point)
- Resolving the next step in a route given the current step + chosen
  disposition

Route graph model
-----------------
The route graph is fully *derived* from input/output disposition lists
attached to each step. There is no separate edge table.

- A step's ``output_dispositions`` list defines the choices an operator
  may make when completing that step.
- A step's ``input_dispositions`` list defines which dispositions, when
  raised at the previous step, route a unit/lot INTO this step.
- A disposition is unique within a route per role: it appears in at most
  one step's input list AND at most one step's output list. This makes
  every (output disposition) → (input disposition) edge unambiguous.
- A step with an empty input list is an entry point (use
  ``ProcessSegment.is_initial_step`` to mark the canonical first step).
- A step with an empty output list is terminal — completing it ends the
  route.

Auto-completion at single-output steps
--------------------------------------
When a step has exactly one output disposition, the routing engine
auto-selects it: callers may pass ``disposition=None`` and the engine
will use that single choice transparently. With zero outputs the route
is terminal. With two or more outputs the caller must specify a
disposition (operator pick).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.core.product_def.models import (
    Disposition,
    OperationsDefinition,
    OperationsDefinitionProductAssignment,
    ProcessSegment,
    ProcessSegmentInputDisposition,
    ProcessSegmentOutputDisposition,
)
from mes.core.operations.models import OperationsRequest
from mes.framework.api.exceptions import NotFoundException
from mes.core.wip.exceptions import NoRouteAssignedException, NoNextStepException

logger = logging.getLogger("mes.routing")


class AmbiguousDispositionError(Exception):
    """Raised when a step has multiple output dispositions but the caller
    did not specify which one to use."""


class RoutingEngineService:
    """Runtime routing engine — resolves step progression for WIP."""

    # ── Order → route resolution ──────────────────────────────────────

    @staticmethod
    async def get_route_for_order(
        session: AsyncSession, order_id: UUID,
    ) -> OperationsDefinition:
        """
        Resolve the process route for a production order.

        Priority:
        1. order.route_id (explicitly assigned route)
        2. Product's default route (is_default=True)
        3. First route found for the product (fallback)
        Raises NoRouteAssignedException if none found.
        """
        stmt = select(OperationsRequest).where(OperationsRequest.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise NotFoundException(resource="OperationsRequest", resource_id=str(order_id))

        if order.route_id is not None:
            route_stmt = (
                select(OperationsDefinition)
                .where(
                    OperationsDefinition.id == order.route_id,
                    OperationsDefinition.is_active.is_(True),
                )
                .options(selectinload(OperationsDefinition.steps))
            )
            route_result = await session.execute(route_stmt)
            route = route_result.scalar_one_or_none()
            if route is not None:
                return route

        default_stmt = (
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == order.product_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_default.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
            .options(selectinload(OperationsDefinition.steps))
        )
        default_result = await session.execute(default_stmt)
        default_route = default_result.scalar_one_or_none()
        if default_route is not None:
            return default_route

        fallback_stmt = (
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == order.product_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
            .options(selectinload(OperationsDefinition.steps))
            .order_by(OperationsDefinition.created_at)
            .limit(1)
        )
        fallback_result = await session.execute(fallback_stmt)
        fallback_route = fallback_result.scalar_one_or_none()
        if fallback_route is not None:
            return fallback_route

        raise NoRouteAssignedException(str(order_id))

    # ── Step navigation ───────────────────────────────────────────────

    @staticmethod
    async def get_first_step(
        session: AsyncSession, order_id: UUID,
    ) -> ProcessSegment:
        """
        Resolve the entry point of the order's route.

        Priority:
        1. The step with ``is_initial_step=True`` (authoritative flag)
        2. The active step with the smallest sequence whose input list is
           empty (UX-derived rule: empty inputs ⇒ entry)
        3. The lowest-sequence active step (last-resort)
        """
        route = await RoutingEngineService.get_route_for_order(session, order_id)
        active = [s for s in route.steps if s.is_active]
        if not active:
            raise NoNextStepException("order:" + str(order_id), None)

        flagged = [s for s in active if s.is_initial_step]
        if flagged:
            return sorted(flagged, key=lambda s: s.sequence)[0]

        # Eager-load input lists for the empty-inputs rule.
        step_ids = [s.id for s in active]
        in_rows = (await session.execute(
            select(ProcessSegmentInputDisposition.step_id).where(
                ProcessSegmentInputDisposition.step_id.in_(step_ids),
                ProcessSegmentInputDisposition.is_active.is_(True),
            )
        )).all()
        steps_with_inputs = {row[0] for row in in_rows}
        no_input = [s for s in active if s.id not in steps_with_inputs]
        if no_input:
            return sorted(no_input, key=lambda s: s.sequence)[0]

        return sorted(active, key=lambda s: s.sequence)[0]

    @staticmethod
    async def get_next_step(
        session: AsyncSession,
        order_id: UUID,
        current_step_id: UUID | None,
        result: str | None = None,  # kept for API compatibility; unused
        disposition: str | None = None,
    ) -> ProcessSegment | None:
        """
        Resolve the next step after ``current_step_id`` for the order.

        Routing rules (derived from input/output disposition lists):

        * ``current_step_id`` is None → return the route's first step.
        * Otherwise look at the current step's output dispositions:
          - 0 outputs → route is complete, return None.
          - 1 output and ``disposition`` is None → auto-select that one.
          - 2+ outputs and ``disposition`` is None → raise
            ``AmbiguousDispositionError`` (caller must pick).
          - ``disposition`` provided → use that name.
        * Find the unique step in the same route whose input list contains
          the chosen disposition. That is the next step. If none exists
          the route is complete (terminal disposition).

        Args:
            disposition: case-sensitive Disposition.name, or None to
                auto-select for single-output steps.
        """
        if current_step_id is None:
            return await RoutingEngineService.get_first_step(session, order_id)

        route = await RoutingEngineService.get_route_for_order(session, order_id)

        # Outputs of the current step (with Disposition rows joined in).
        out_stmt = (
            select(Disposition)
            .join(
                ProcessSegmentOutputDisposition,
                ProcessSegmentOutputDisposition.disposition_id == Disposition.id,
            )
            .where(
                ProcessSegmentOutputDisposition.step_id == current_step_id,
                ProcessSegmentOutputDisposition.is_active.is_(True),
                Disposition.is_active.is_(True),
            )
            .order_by(ProcessSegmentOutputDisposition.position)
        )
        outputs = list((await session.execute(out_stmt)).scalars().all())

        if not outputs:
            logger.info(
                "Step %s has no output dispositions — terminal step in route %s",
                current_step_id, route.id,
            )
            return None

        # Resolve the chosen disposition.
        chosen: Disposition | None = None
        if disposition is None:
            if len(outputs) == 1:
                chosen = outputs[0]
                logger.info(
                    "Auto-selecting single output disposition %r at step %s",
                    chosen.name, current_step_id,
                )
            else:
                names = ", ".join(repr(o.name) for o in outputs)
                raise AmbiguousDispositionError(
                    f"Step {current_step_id} has {len(outputs)} output "
                    f"dispositions ({names}); caller must specify one."
                )
        else:
            for o in outputs:
                if o.name == disposition or o.code == disposition:
                    chosen = o
                    break
            if chosen is None:
                names = ", ".join(repr(o.name) for o in outputs)
                raise NoNextStepException(
                    f"step:{current_step_id}",
                    f"disposition {disposition!r} not in output list ({names})",
                )

        # Find the unique step in this route whose input list contains the
        # chosen disposition.
        next_stmt = (
            select(ProcessSegment)
            .join(
                ProcessSegmentInputDisposition,
                ProcessSegmentInputDisposition.step_id == ProcessSegment.id,
            )
            .where(
                ProcessSegment.route_id == route.id,
                ProcessSegment.is_active.is_(True),
                ProcessSegmentInputDisposition.disposition_id == chosen.id,
                ProcessSegmentInputDisposition.is_active.is_(True),
            )
        )
        rows = (await session.execute(next_stmt)).scalars().all()
        if not rows:
            logger.info(
                "Disposition %r at step %s has no destination — terminal",
                chosen.name, current_step_id,
            )
            return None
        if len(rows) > 1:
            # Should be prevented by the uniqueness validation in
            # ProductDefService.set_step_input_dispositions, but guard here.
            ids = ", ".join(str(s.id) for s in rows)
            raise RuntimeError(
                f"Disposition {chosen.id} ({chosen.name!r}) is in the input "
                f"list of multiple steps ({ids}) in route {route.id}; "
                f"data integrity violation."
            )
        return rows[0]

    # ── Disposition introspection ────────────────────────────────────

    @staticmethod
    async def get_available_dispositions(
        session: AsyncSession,
        step_id: UUID,
    ) -> list[dict[str, str]]:
        """
        Return the output dispositions available at a step.

        Each entry is ``{id, name, description, category, to_step_id}``
        where ``to_step_id`` is the step that has the disposition in its
        input list (omitted if there is no destination — terminal).
        Returns an empty list for terminal steps (no outputs).
        """
        # Step's outputs (Disposition rows).
        out_stmt = (
            select(Disposition)
            .join(
                ProcessSegmentOutputDisposition,
                ProcessSegmentOutputDisposition.disposition_id == Disposition.id,
            )
            .where(
                ProcessSegmentOutputDisposition.step_id == step_id,
                ProcessSegmentOutputDisposition.is_active.is_(True),
                Disposition.is_active.is_(True),
            )
            .order_by(ProcessSegmentOutputDisposition.position)
        )
        outputs = list((await session.execute(out_stmt)).scalars().all())
        if not outputs:
            return []

        # Resolve each disposition's destination step (if any).
        # Need the route id; fetch from the step.
        step_route_stmt = select(ProcessSegment.route_id).where(
            ProcessSegment.id == step_id,
        )
        route_id = (await session.execute(step_route_stmt)).scalar_one_or_none()

        dest_map: dict[UUID, UUID] = {}
        if route_id is not None:
            dest_stmt = (
                select(
                    ProcessSegmentInputDisposition.disposition_id,
                    ProcessSegment.id,
                )
                .join(
                    ProcessSegment,
                    ProcessSegment.id == ProcessSegmentInputDisposition.step_id,
                )
                .where(
                    ProcessSegment.route_id == route_id,
                    ProcessSegment.is_active.is_(True),
                    ProcessSegmentInputDisposition.is_active.is_(True),
                    ProcessSegmentInputDisposition.disposition_id.in_(
                        [o.id for o in outputs]
                    ),
                )
            )
            for disp_id, dest_step_id in (await session.execute(dest_stmt)).all():
                dest_map[disp_id] = dest_step_id

        out: list[dict[str, str]] = []
        for d in outputs:
            entry: dict[str, str] = {
                "id": str(d.id),
                "name": d.name,
                "code": d.code,
                "description": d.description or "",
                "category": d.category,
            }
            dest = dest_map.get(d.id)
            if dest is not None:
                entry["to_step_id"] = str(dest)
            out.append(entry)
        return out

    @staticmethod
    async def get_process_segments(
        session: AsyncSession, order_id: UUID,
    ) -> list[ProcessSegment]:
        """Get all active steps for an order's route, sorted by sequence."""
        route = await RoutingEngineService.get_route_for_order(session, order_id)
        steps = sorted(route.steps, key=lambda s: s.sequence)
        return [s for s in steps if s.is_active]

    # ── Route integrity validation ───────────────────────────────────

    @staticmethod
    async def validate_route(
        session: AsyncSession, route_id: UUID,
    ) -> dict:
        """
        Validate the integrity of a route's disposition graph.

        Checks performed:
        - Empty route: warning only (legitimate while editing).
        - Entry point: exactly one step with ``is_initial_step=True``, OR
          if none flagged, exactly one step with an empty input list.
        - Output dispositions: every output disposition on every step
          must appear as an input on some other step in the same route
          (otherwise it is an unconnected dead-end).
        - Input dispositions: every input disposition on every step
          must appear as an output on some other step in the same route
          (otherwise the step is unreachable through that input).
        - Disposition uniqueness: each disposition is in at most one
          step's input list AND at most one step's output list within
          the route.
        - Orphan steps: every active step must be reachable from the
          entry step by following output→input disposition edges.

        Empty input list ⇒ entry point (allowed).
        Empty output list ⇒ terminal step (allowed; at least one
        terminal is required when the route has steps).

        Returns:
            ``{"valid": bool, "errors": [str], "warnings": [str],
               "stats": {...}}``
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Load the route with all steps + disposition lists eager-loaded.
        stmt = (
            select(OperationsDefinition)
            .where(OperationsDefinition.id == route_id)
            .options(
                selectinload(OperationsDefinition.steps).selectinload(
                    ProcessSegment.input_dispositions
                ).selectinload(ProcessSegmentInputDisposition.disposition),
                selectinload(OperationsDefinition.steps).selectinload(
                    ProcessSegment.output_dispositions
                ).selectinload(ProcessSegmentOutputDisposition.disposition),
            )
        )
        route = (await session.execute(stmt)).scalar_one_or_none()
        if route is None:
            raise NotFoundException(resource="OperationsDefinition", resource_id=str(route_id))

        steps = [s for s in route.steps if s.is_active]
        steps.sort(key=lambda s: s.sequence)

        stats = {
            "step_count": len(steps),
            "initial_step_count": 0,
            "terminal_step_count": 0,
            "output_disposition_count": 0,
            "input_disposition_count": 0,
        }

        if not steps:
            warnings.append("Route has no active steps.")
            return {"valid": True, "errors": errors, "warnings": warnings, "stats": stats}

        # Build per-step input/output disposition-id sets.
        step_inputs: dict[UUID, list[UUID]] = {}
        step_outputs: dict[UUID, list[UUID]] = {}
        # Reverse maps for uniqueness checks.
        input_owner: dict[UUID, list[UUID]] = {}   # disp_id -> [step_id]
        output_owner: dict[UUID, list[UUID]] = {}  # disp_id -> [step_id]
        disp_name: dict[UUID, str] = {}

        for st in steps:
            ins = [r.disposition_id for r in st.input_dispositions if r.is_active]
            outs = [r.disposition_id for r in st.output_dispositions if r.is_active]
            step_inputs[st.id] = ins
            step_outputs[st.id] = outs
            for r in st.input_dispositions:
                if r.is_active:
                    input_owner.setdefault(r.disposition_id, []).append(st.id)
                    disp_name[r.disposition_id] = r.disposition.name
            for r in st.output_dispositions:
                if r.is_active:
                    output_owner.setdefault(r.disposition_id, []).append(st.id)
                    disp_name[r.disposition_id] = r.disposition.name
            if not outs:
                stats["terminal_step_count"] += 1
            if st.is_initial_step:
                stats["initial_step_count"] += 1

        stats["input_disposition_count"] = sum(len(v) for v in step_inputs.values())
        stats["output_disposition_count"] = sum(len(v) for v in step_outputs.values())

        step_label = {s.id: f"#{s.sequence} {s.name!r}" for s in steps}

        # ── Entry point check ───────────────────────────────────────
        flagged = [s for s in steps if s.is_initial_step]
        no_input = [s for s in steps if not step_inputs[s.id]]
        if len(flagged) > 1:
            labels = ", ".join(step_label[s.id] for s in flagged)
            errors.append(
                f"Multiple steps marked is_initial_step=True: {labels}. "
                f"Exactly one initial step is allowed."
            )
        if not flagged:
            if len(no_input) == 0:
                errors.append(
                    "No entry point: no step has is_initial_step=True and "
                    "no step has an empty input disposition list."
                )
            elif len(no_input) > 1:
                labels = ", ".join(step_label[s.id] for s in no_input)
                errors.append(
                    f"Ambiguous entry point: {len(no_input)} steps have empty "
                    f"input lists ({labels}) and none is marked "
                    f"is_initial_step=True."
                )
        # The initial step must have no input dispositions (it is the
        # entry point of the route — nothing routes *to* it).
        for s in flagged:
            if step_inputs[s.id]:
                disp_labels = ", ".join(
                    repr(disp_name[d]) for d in step_inputs[s.id]
                )
                errors.append(
                    f"Initial step {step_label[s.id]} must have an empty "
                    f"input disposition list, but has: {disp_labels}."
                )

        # ── Disposition uniqueness ──────────────────────────────────
        # Input uniqueness is required: a disposition must uniquely identify
        # a destination step. Output uniqueness is NOT enforced — multiple
        # steps may produce the same disposition (enabling shared sinks and
        # self-loops where a step's output matches its own input).
        for disp_id, owners in input_owner.items():
            if len(owners) > 1:
                labels = ", ".join(step_label[sid] for sid in owners)
                errors.append(
                    f"Disposition {disp_name[disp_id]!r} is in the input "
                    f"list of multiple steps: {labels}."
                )

        # ── Connectedness of dispositions ────────────────────────────
        for st in steps:
            for disp_id in step_outputs[st.id]:
                if disp_id not in input_owner:
                    errors.append(
                        f"Output disposition {disp_name[disp_id]!r} on step "
                        f"{step_label[st.id]} is not in any step's input list "
                        f"(unconnected output / dead-end)."
                    )
            for disp_id in step_inputs[st.id]:
                if disp_id not in output_owner:
                    errors.append(
                        f"Input disposition {disp_name[disp_id]!r} on step "
                        f"{step_label[st.id]} is not in any step's output list "
                        f"(unreachable input)."
                    )

        # ── Terminal step required ───────────────────────────────────
        if stats["terminal_step_count"] == 0:
            errors.append(
                "Route has no terminal step (no step with an empty output "
                "disposition list)."
            )

        # ── Reachability / orphan steps ─────────────────────────────
        entry: ProcessSegment | None = None
        if flagged:
            entry = sorted(flagged, key=lambda s: s.sequence)[0]
        elif len(no_input) == 1:
            entry = no_input[0]

        if entry is not None:
            # BFS via output disposition → step that has it as input.
            reachable: set[UUID] = {entry.id}
            frontier = [entry.id]
            while frontier:
                cur = frontier.pop()
                for disp_id in step_outputs.get(cur, []):
                    for nxt in input_owner.get(disp_id, []):
                        if nxt not in reachable:
                            reachable.add(nxt)
                            frontier.append(nxt)
            for st in steps:
                if st.id not in reachable:
                    errors.append(
                        f"Orphan step {step_label[st.id]}: not reachable from "
                        f"entry step {step_label[entry.id]}."
                    )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }
