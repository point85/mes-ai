/* RT-CLIENT TypeScript types — mirrors server Pydantic schemas */

// ── Genealogy / Traceability ──────────────────────────────────────

export interface GenealogyStepRecord {
  step_id: string | null;
  step_sequence: number | null;
  step_name: string | null;
  entered_at: string | null;
  exited_at: string | null;
  result: string | null;
  equipment_id: string | null;
  equipment_name: string | null;
  data_snapshot: Record<string, unknown> | null;
}

export interface GenealogyMaterialRecord {
  material_lot_id: string;
  material_code: string | null;
  material_name: string | null;
  lot_number: string | null;
  quantity_consumed: number;
  consumed_at: string;
  step_id: string | null;
}

export interface GenealogyTestRecord {
  result_id: string;
  test_code: string | null;
  test_name: string | null;
  result: string;
  measured_values: Record<string, unknown> | null;
  tested_at: string;
  equipment_id: string | null;
}

export interface GenealogyDataRecord {
  data_point_id: string;
  definition_code: string | null;
  definition_name: string | null;
  value_numeric: number | null;
  value_string: string | null;
  value_boolean: boolean | null;
  collected_at: string;
}

export interface GenealogyRecord {
  unit_id: string | null;
  lot_id: string | null;
  serial_number: string | null;
  lot_number: string | null;
  order_id: string | null;
  order_number: string | null;
  product_id: string | null;
  product_name: string | null;
  status: string | null;
  steps: GenealogyStepRecord[];
  materials: GenealogyMaterialRecord[];
  test_results: GenealogyTestRecord[];
  data_points: GenealogyDataRecord[];
}

// ── Physical Model (S95 hierarchy) ────────────────────────────────

export interface Site {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  is_active: boolean;
}

export interface Area {
  id: string;
  name: string;
  code: string;
  site_id: string;
  description?: string | null;
  is_active: boolean;
}

export interface ProductionLine {
  id: string;
  name: string;
  code: string;
  area_id: string;
  description?: string | null;
  is_active: boolean;
}

export interface WorkCell {
  id: string;
  name: string;
  code: string;
  line_id: string;
  description?: string | null;
  default_dispatch_strategy: string | null;
  is_active: boolean;
}

export interface Equipment {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  work_cell_id: string;
  equipment_class_id?: string | null;
  state_model_id?: string | null;
  max_queue_depth?: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentCurrentState {
  equipment_id: string;
  state_model: string;
  state: string;
  dispatch_category: string;
  oee_bucket: string;
  started_at?: string | null;
}

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
  status: "queued" | "in_process" | "completed" | "scrapped" | "on_hold";
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
  status: "queued" | "in_process" | "completed" | "scrapped" | "on_hold";
  is_active: boolean;
  uom_symbol: string | null;
  hold_reason: string | null;
  release_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface UnitHistory {
  id: string;
  unit_id: string;
  step_id: string;
  equipment_id: string | null;
  entered_at: string;
  exited_at: string | null;
  result: string | null;
  operator_id: string | null;
  data_snapshot: Record<string, unknown> | null;
  created_at: string;
}

export interface LotHistory {
  id: string;
  lot_id: string;
  step_id: string;
  equipment_id: string | null;
  entered_at: string;
  exited_at: string | null;
  quantity_in: number;
  quantity_out: number;
  quantity_scrapped: number;
  operator_id: string | null;
  created_at: string;
}

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

export interface ProductionOrder {
  id: string;
  order_number: string;
  product_id: string;
  route_id: string | null;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  status: string;
  priority: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  erp_reference: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrderProgress {
  order_id: string;
  order_number: string;
  product_id: string;
  status: string;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  units_queued: number;
  units_in_process: number;
  units_completed: number;
  units_on_hold: number;
  units_scrapped: number;
  lots_queued: number;
  lots_in_process: number;
  lots_completed: number;
  lots_on_hold: number;
  lots_scrapped: number;
}

export interface MESEvent {
  event_type: string;
  source: string;
  payload: Record<string, unknown>;
  timestamp: string;
  event_id: string;
}

export interface DispatchStrategyInfo {
  name: string;
  description: string;
  strategy_type: string;
}

export interface DispatchOption {
  equipment_id: string;
  equipment_code: string;
  equipment_name: string;
  work_cell_id: string;
  work_cell_code: string;
  work_cell_name: string | null;
  step_id: string;
  step_name: string | null;
  dispatch_category: string | null;
  material_setup: boolean;
  queue_depth: number;
  max_queue_depth: number | null;
  score: number;
  reason: string | null;
  eligible: boolean;
}

export interface DispatchEvaluateResponse {
  unit_id: string | null;
  lot_id: string | null;
  strategy: string;
  options: DispatchOption[];
  excluded_options: DispatchOption[];
  recommended: DispatchOption | null;
  blocked: boolean;
  blocked_reason: string | null;
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

// ── Material Management ──────────────────────────────────────────

export interface MaterialSetup {
  equipment_material_id: string | null;
  material_id: string | null;
  material_code: string | null;
  material_name: string | null;
  design_speed: number | null;
  design_speed_uom_id: string | null;
  job_number: string | null;
  setup_at: string | null;
}

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

// ── Inventory Management ─────────────────────────────────────────

export interface InventoryBalance {
  id: string;
  material_lot_id: string;
  location_id: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryTransaction {
  id: string;
  transaction_type: string;
  material_lot_id: string;
  from_location_id: string | null;
  to_location_id: string | null;
  quantity: number;
  reference_id: string | null;
  reference_type: string | null;
  reason: string | null;
  performed_at: string;
  performed_at_utc: string | null;
  created_at: string;
}

export interface StorageLocation {
  id: string;
  name: string;
  code: string;
  description: string | null;
  location_type: string;
  aisle: string | null;
  bay: string | null;
  tier: string | null;
  site_id: string | null;
  capacity: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
// ── Performance ──────────────────────────────────────────────────

export interface EquipmentStateLog {
  id: string;
  equipment_id: string;
  state_model: string;
  state: string;
  sub_state: string | null;
  dispatch_category: string;
  oee_bucket: string;
  started_at: string;
  ended_at: string | null;
  reason_code: string | null;
  notes: string | null;
}

export interface ProductionCounter {
  id: string;
  equipment_id: string;
  order_id: string | null;
  shift_date: string;
  good_count: number;
  reject_count: number;
  rework_count: number;
  ideal_cycle_time_sec: number | null;
  actual_run_time_sec: number | null;
}

export interface StateChangeRequest {
  equipment_id: string;
  state_model: string;
  state: string;
  sub_state?: string;
  dispatch_category: string;
  oee_bucket: string;
  started_at: string;
  reason_code?: string;
  notes?: string;
}

export interface CounterCreateUpdate {
  equipment_id: string;
  order_id?: string;
  shift_date: string;
  good_count: number;
  reject_count: number;
  rework_count: number;
  ideal_cycle_time_sec?: number;
  actual_run_time_sec?: number;
}