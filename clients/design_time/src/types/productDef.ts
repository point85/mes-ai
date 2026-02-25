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
  product_id: string;
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
  work_center_id: string | null;
  expected_cycle_time_sec: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteStepCreate {
  sequence: number;
  name: string;
  step_type?: string;
  work_center_id?: string | null;
  expected_cycle_time_sec?: number | null;
}

export interface RouteStepUpdate {
  sequence?: number;
  name?: string;
  step_type?: string;
  work_center_id?: string | null;
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
