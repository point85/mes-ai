/**
 * Dispatching Engine: TypeScript types mirroring server Pydantic schemas.
 */

export interface DispatchEvaluateRequest {
  unit_id?: string | null;
  lot_id?: string | null;
  strategy?: string;
}

export interface DispatchOption {
  equipment_id: string;
  equipment_code: string;
  equipment_name: string;
  work_cell_id: string;
  work_cell_code: string;
  step_id: string;
  step_name: string | null;
  queue_depth: number;
  score: number;
  reason: string | null;
}

export interface DispatchEvaluateResponse {
  unit_id: string | null;
  lot_id: string | null;
  strategy: string;
  options: DispatchOption[];
  recommended: DispatchOption | null;
}

export interface DispatchExecuteRequest {
  unit_id?: string | null;
  lot_id?: string | null;
  destination_equipment_id: string;
  destination_step_id: string;
}

export interface DispatchExecuteResponse {
  unit_id: string | null;
  lot_id: string | null;
  destination_equipment_id: string;
  destination_step_id: string;
  dispatched_at: string;
}

export interface DispatchStrategyInfo {
  name: string;
  description: string;
  strategy_type: string;
}

export interface DispatchQueueItem {
  unit_id: string | null;
  lot_id: string | null;
  serial_number: string | null;
  lot_number: string | null;
  order_id: string | null;
  current_step_id: string | null;
  status: string;
  equipment_id: string | null;
}
