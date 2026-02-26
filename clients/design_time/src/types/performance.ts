/**
 * Performance Analysis: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Equipment State Log ──────────────────────────────────────────────

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
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StateChangeRequest {
  equipment_id: string;
  state_model?: string;
  state: string;
  sub_state?: string | null;
  dispatch_category: string;
  oee_bucket: string;
  started_at: string;
  reason_code?: string | null;
  notes?: string | null;
}

// ─── Production Counter ───────────────────────────────────────────────

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
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CounterCreateUpdate {
  equipment_id: string;
  order_id?: string | null;
  shift_date: string;
  good_count?: number;
  reject_count?: number;
  rework_count?: number;
  ideal_cycle_time_sec?: number | null;
  actual_run_time_sec?: number | null;
}

// ─── OEE Result ───────────────────────────────────────────────────────

export interface OEEResult {
  equipment_id: string;
  period_start: string;
  period_end: string;
  availability: number;
  performance: number;
  quality: number;
  oee: number;
  details: Record<string, unknown> | null;
}
