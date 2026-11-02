/* WIP-CLIENT TypeScript types — mirrors server Pydantic schemas.
   Trimmed copy of clients/run_time/src/types/index.ts: only the types the
   single-screen WIP workflow needs (see docs/WIP_CLIENT_PLAN.md §6.5). */

// ── WIP ──────────────────────────────────────────────────────────

export interface Unit {
  id: string;
  serial_number: string;
  order_id: string;
  order_number: string | null;
  product_id: string;
  material_id: string | null;
  current_step_id: string | null;
  current_step_name: string | null;
  current_equipment_id: string | null;
  status: "queued" | "in_process" | "completed" | "finished" | "scrapped" | "on_hold";
  is_active: boolean;
  hold_reason: string | null;
  release_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface Lot {
  id: string;
  lot_number: string;
  order_id: string;
  order_number: string | null;
  product_id: string;
  quantity: number;
  material_id: string | null;
  current_step_id: string | null;
  current_step_name: string | null;
  current_equipment_id: string | null;
  status: "queued" | "in_process" | "completed" | "finished" | "scrapped" | "on_hold";
  is_active: boolean;
  uom_symbol: string | null;
  hold_reason: string | null;
  release_reason: string | null;
  created_at: string;
  updated_at: string;
}

// ── Routing ──────────────────────────────────────────────────────

export interface RouteStep {
  id: string;
  route_id: string;
  name: string;
  code: string;
  description: string | null;
  step_type: string;
  sequence: number;
  equipment_class_id: string | null;
  erp_operation_number: string | null;
  disposition_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StepParameter {
  id: string;
  step_id: string;
  name: string;
  data_type: string;
  uom_id: string | null;
  uom_symbol: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  target_value: number | null;
  is_required: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DataDefinition {
  id: string;
  name: string;
  code: string;
  description: string | null;
  data_type: string;
  uom_id: string | null;
  uom_symbol: string | null;
  step_id: string | null;
  source: string;
  is_required: boolean;
  enum_values: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Disposition {
  id: string;
  name: string;
  code: string;
  description: string;
  category: string;
  /** UUID of the step that consumes this disposition; absent for terminal edges. */
  to_step_id?: string;
  /** @deprecated Legacy transition-based disposition */
  label?: string;
}

export interface DispositionCatalog {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
  is_active: boolean;
}

// ── Data collection (persisted values) ──────────────────────────

export interface DataPoint {
  id: string;
  definition_id: string;
  unit_id: string | null;
  lot_id: string | null;
  value_numeric: number | null;
  value_string: string | null;
  value_boolean: boolean | null;
  collected_at: string;
  collected_at_utc: string | null;
  source_equipment_id: string | null;
  operator_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** A recorded step-parameter actual value for a WIP unit/lot. */
export interface StepParameterValue {
  id: string;
  parameter_id: string;
  unit_id: string | null;
  lot_id: string | null;
  value_numeric: number | null;
  value_string: string | null;
  value_boolean: boolean | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Step Context (one-call screen payload) ───────────────────────

export interface StepContext {
  wip_type: "unit" | "lot";
  wip: Unit | Lot;
  step: RouteStep | null;
  step_parameters: StepParameter[];
  data_definitions: DataDefinition[];
  dispositions: Disposition[];
  route_steps: RouteStep[];
  outgoing_conditions?: string[];
}

// ── Equipment at step ────────────────────────────────────────────

export interface EquipmentCurrentState {
  equipment_id: string;
  state_model: string;
  state: string;
  dispatch_category: string;
  oee_bucket: string;
  started_at?: string | null;
}

export interface StepEquipmentStatus {
  equipment_id: string;
  equipment_code: string;
  equipment_name: string | null;
  dispatch_category: string | null;
  state_model: string | null;
  state: string | null;
  queue_depth: number;
  max_queue_depth: number | null;
  has_spare_capacity: boolean;
  material_setup: boolean;
  is_assigned: boolean;
}

// ── Product (name display on the info card) ──────────────────────

export interface Product {
  id: string;
  name: string;
  code: string;
  description: string | null;
  product_type: string;
  uom_id?: string | null;
  uom_symbol?: string | null;
  is_active: boolean;
}

// ── Material consumption (BOM picking) ───────────────────────────

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

export interface Material {
  id: string;
  name: string;
  code: string;
  description: string | null;
  material_type: string;
  uom_id: string;
  uom_symbol: string | null;
  tracking_method: "lot" | "unit";
  revision: string | null;
  shelf_life_days: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialLot {
  id: string;
  material_id: string;
  lot_number: string;
  tracking_method: "lot" | "unit";
  quantity_on_hand: number;
  quantity_reserved: number;
  status: string;
  received_date: string | null;
  expiry_date: string | null;
  supplier: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialConsumption {
  id: string;
  material_lot_id: string;
  unit_id: string | null;
  lot_id: string | null;
  step_id: string | null;
  quantity_consumed: number;
  consumed_at: string;
  consumed_at_utc: string | null;
  created_at: string;
  created_at_utc: string | null;
}

