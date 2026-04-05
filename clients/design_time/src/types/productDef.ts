/**
 * Product Definition: TypeScript types mirroring server Pydantic schemas.
 * Hierarchy: Product → BOM → BOMItem, Product → Route → Step → StepParameter
 */

// ─── Product ──────────────────────────────────────────────────────────

export interface Product {
  id: string;
  name: string;
  code: string;
  version: string;
  description: string | null;
  uom: string;
  product_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  name: string;
  code: string;
  version?: string;
  description?: string | null;
  uom?: string;
  product_type?: string;
}

export interface ProductUpdate {
  name?: string;
  code?: string;
  version?: string;
  description?: string | null;
  uom?: string;
  product_type?: string;
}

// ─── BOM ──────────────────────────────────────────────────────────────

export interface BOM {
  id: string;
  product_id: string;
  version: string;
  effective_date: string | null;
  expiry_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BOMCreate {
  version?: string;
  effective_date?: string | null;
  expiry_date?: string | null;
}

export interface BOMUpdate {
  version?: string;
  effective_date?: string | null;
  expiry_date?: string | null;
}

// ─── BOM Item ─────────────────────────────────────────────────────────

export interface BOMItem {
  id: string;
  bom_id: string;
  material_code: string;
  quantity: number;
  uom: string;
  position: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BOMItemCreate {
  material_code: string;
  quantity: number;
  uom?: string;
  position?: number;
}

// ─── Route ────────────────────────────────────────────────────────────

export interface ProcessRoute {
  id: string;
  product_id: string | null;
  version: string;
  name: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteCreate {
  name: string;
  version?: string;
  description?: string | null;
  is_default?: boolean;
}

export interface RouteUpdate {
  name?: string;
  version?: string;
  description?: string | null;
  is_default?: boolean;
}

// ─── Route Step ───────────────────────────────────────────────────────

export interface RouteStep {
  id: string;
  route_id: string;
  sequence: number;
  name: string;
  step_type: string;
  work_cell_id: string | null;
  expected_cycle_time_sec: number | null;
  erp_operation_number: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteStepCreate {
  sequence: number;
  name: string;
  step_type?: string;
  work_cell_id?: string | null;
  expected_cycle_time_sec?: number | null;
}

export interface RouteStepUpdate {
  sequence?: number;
  name?: string;
  step_type?: string;
  work_cell_id?: string | null;
  expected_cycle_time_sec?: number | null;
}

// ─── Step Parameter ───────────────────────────────────────────────────

export interface StepParameter {
  id: string;
  step_id: string;
  name: string;
  data_type: string;
  uom: string | null;
  target_value: string | null;
  lower_limit: string | null;
  upper_limit: string | null;
  is_required: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StepParameterCreate {
  name: string;
  data_type?: string;
  uom?: string | null;
  target_value?: string | null;
  lower_limit?: string | null;
  upper_limit?: string | null;
  is_required?: boolean;
}

// ─── Step Transition ──────────────────────────────────────────────────

export interface StepTransition {
  id: string;
  from_step_id: string;
  to_step_id: string;
  condition: string;
  is_default: boolean;
  priority: number;
  label: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StepTransitionCreate {
  to_step_id: string;
  condition?: string;
  is_default?: boolean;
  priority?: number;
  label?: string | null;
}

export interface StepTransitionUpdate {
  to_step_id?: string;
  condition?: string;
  is_default?: boolean;
  priority?: number;
  label?: string | null;
}

// ─── Route–Product Assignment ─────────────────────────────────────────

export interface RouteProductAssignment {
  id: string;
  route_id: string;
  product_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteProductAssignmentCreate {
  product_id: string;
}

// ─── Route–Material Assignment ────────────────────────────────────────

export interface RouteMaterialAssignment {
  id: string;
  route_id: string;
  material_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteMaterialAssignmentCreate {
  material_id: string;
}
