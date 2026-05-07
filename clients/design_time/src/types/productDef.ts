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
  uom_id: string;
  uom_symbol: string | null;
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
  uom_id: string;
  product_type?: string;
}

export interface ProductUpdate {
  name?: string;
  code?: string;
  version?: string;
  description?: string | null;
  uom_id?: string;
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
  uom_id: string;
  uom_symbol: string | null;
  position: number;
  process_segment_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BOMItemCreate {
  material_code: string;
  quantity: number;
  uom_id: string;
  position?: number;
  process_segment_id?: string | null;
}

export interface BOMItemUpdate {
  material_code?: string;
  quantity?: number;
  uom_id?: string;
  position?: number;
  process_segment_id?: string | null;
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

// ─── Disposition ──────────────────────────────────────────────────────

export interface Disposition {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DispositionCreate {
  code: string;
  name: string;
  description?: string | null;
  category?: string;
}

export interface DispositionUpdate {
  name?: string;
  description?: string | null;
  category?: string;
}

// ─── Route Step ───────────────────────────────────────────────────────

export interface RouteStep {
  id: string;
  route_id: string;
  sequence: number;
  name: string;
  step_type: string;
  work_cell_id: string | null;
  equipment_class_id: string | null;
  expected_cycle_time_sec: number | null;
  erp_operation_number: string | null;
  is_initial_step: boolean;
  input_dispositions: Disposition[];
  output_dispositions: Disposition[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteStepCreate {
  sequence: number;
  name: string;
  step_type?: string;
  work_cell_id?: string | null;
  equipment_class_id?: string | null;
  expected_cycle_time_sec?: number | null;
  is_initial_step?: boolean;
  input_disposition_ids?: string[];
  output_disposition_ids?: string[];
}

export interface RouteStepUpdate {
  sequence?: number;
  name?: string;
  step_type?: string;
  work_cell_id?: string | null;
  equipment_class_id?: string | null;
  expected_cycle_time_sec?: number | null;
  is_initial_step?: boolean;
  input_disposition_ids?: string[];
  output_disposition_ids?: string[];
}

// ─── Route Validation ─────────────────────────────────────────────────

export interface RouteValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  stats: {
    step_count?: number;
    initial_step_count?: number;
    terminal_step_count?: number;
    input_disposition_count?: number;
    output_disposition_count?: number;
    [key: string]: number | undefined;
  };
}

// ─── Step Equipment Requirement (ISA-95 Process Segment) ─────────────

export type EquipmentRequirementUseType = "required" | "preferred" | "alternate";

export interface StepEquipmentRequirement {
  id: string;
  step_id: string;
  equipment_class_id: string | null;
  equipment_id: string | null;
  use_type: EquipmentRequirementUseType;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StepEquipmentRequirementCreate {
  equipment_class_id?: string | null;
  equipment_id?: string | null;
  use_type?: EquipmentRequirementUseType;
  description?: string | null;
}

export interface StepEquipmentRequirementUpdate {
  use_type?: EquipmentRequirementUseType;
  description?: string | null;
}

// ─── Step Material Requirement (ISA-95 Process Segment) ──────────────

export type MaterialUse = "consumed" | "produced";

export interface StepMaterialRequirement {
  id: string;
  step_id: string;
  material_id: string;
  quantity: number;
  uom_id: string;
  uom_symbol: string | null;
  material_use: MaterialUse;
  position: number;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StepMaterialRequirementCreate {
  material_id: string;
  quantity: number;
  uom_id: string;
  material_use?: MaterialUse;
  position?: number;
  description?: string | null;
}

export interface StepMaterialRequirementUpdate {
  quantity?: number;
  uom_id?: string;
  material_use?: MaterialUse;
  position?: number;
  description?: string | null;
}

// ─── Step Parameter ───────────────────────────────────────────────────

export interface StepParameter {
  id: string;
  step_id: string;
  name: string;
  data_type: string;
  uom_id: string | null;
  uom_symbol: string | null;
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
  uom_id?: string | null;
  target_value?: string | null;
  lower_limit?: string | null;
  upper_limit?: string | null;
  is_required?: boolean;
}

export interface StepParameterUpdate {
  name?: string;
  data_type?: string;
  uom_id?: string | null;
  target_value?: string | null;
  lower_limit?: string | null;
  upper_limit?: string | null;
  is_required?: boolean;
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
