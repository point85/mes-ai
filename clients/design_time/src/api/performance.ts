/**
 * Performance Analysis API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  EquipmentStateLog,
  EquipmentStateModel,
  StateChangeRequest,
  ProductionCounter,
  CounterCreateUpdate,
  OEEResult,
  Reason,
  ReasonCreate,
  ReasonUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Reasons ──────────────────────────────────────────────────────────

export async function fetchReasons(): Promise<Reason[]> {
  const { data } = await api.get<ApiResponse<Reason[]>>("/performance/reasons");
  return data.data;
}

export async function createReason(body: ReasonCreate): Promise<Reason> {
  const { data } = await api.post<ApiResponse<Reason>>("/performance/reasons", body);
  return data.data;
}

export async function updateReason(id: string, body: ReasonUpdate): Promise<Reason> {
  const { data } = await api.put<ApiResponse<Reason>>(`/performance/reasons/${id}`, body);
  return data.data;
}

export async function deleteReason(id: string): Promise<void> {
  await api.delete(`/performance/reasons/${id}`);
}

// ─── State Models ─────────────────────────────────────────────────────

export async function fetchStateModels(): Promise<EquipmentStateModel[]> {
  const { data } = await api.get<ApiResponse<EquipmentStateModel[]>>(
    "/performance/state-models",
  );
  return data.data;
}

// ─── OEE ──────────────────────────────────────────────────────────────

export async function calculateOEE(
  equipmentId: string,
  periodStart: string,
  periodEnd: string,
): Promise<OEEResult> {
  const { data } = await api.get<ApiResponse<OEEResult>>("/performance/oee", {
    params: {
      equipment_id: equipmentId,
      period_start: periodStart,
      period_end: periodEnd,
    },
  });
  return data.data;
}

// ─── Equipment State Logs ─────────────────────────────────────────────

export async function fetchEquipmentStates(
  equipmentId?: string,
): Promise<ApiListResponse<EquipmentStateLog>> {
  const params: Record<string, string> = { limit: "200" };
  if (equipmentId) params.equipment_id = equipmentId;
  const { data } = await api.get<ApiListResponse<EquipmentStateLog>>(
    "/performance/equipment-states",
    { params },
  );
  return data;
}

export async function recordStateChange(
  body: StateChangeRequest,
): Promise<EquipmentStateLog> {
  const { data } = await api.post<ApiResponse<EquipmentStateLog>>(
    "/performance/equipment-states",
    body,
  );
  return data.data;
}

// ─── Production Counters ──────────────────────────────────────────────

export async function fetchCounters(
  equipmentId?: string,
  shiftDate?: string,
): Promise<ApiListResponse<ProductionCounter>> {
  const params: Record<string, string> = { limit: "200" };
  if (equipmentId) params.equipment_id = equipmentId;
  if (shiftDate) params.shift_date = shiftDate;
  const { data } = await api.get<ApiListResponse<ProductionCounter>>(
    "/performance/counters",
    { params },
  );
  return data;
}

export async function createOrUpdateCounter(
  body: CounterCreateUpdate,
): Promise<ProductionCounter> {
  const { data } = await api.post<ApiResponse<ProductionCounter>>(
    "/performance/counters",
    body,
  );
  return data.data;
}
