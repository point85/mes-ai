/**
 * TanStack Query hooks for Performance Analysis.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchEquipmentStates,
  fetchStateModels,
  recordStateChange,
  fetchCounters,
  createOrUpdateCounter,
  calculateOEE,
  fetchReasons,
  createReason,
  updateReason,
  deleteReason,
} from "../api/performance";
import type { StateChangeRequest, CounterCreateUpdate, ReasonCreate, ReasonUpdate } from "../types";

const KEYS = {
  reasons: ["reasons"] as const,
  stateModels: ["stateModels"] as const,
  states: ["equipmentStates"] as const,
  stateList: (equipmentId?: string) =>
    ["equipmentStates", "list", equipmentId] as const,
  counters: ["productionCounters"] as const,
  counterList: (equipmentId?: string, shiftDate?: string) =>
    ["productionCounters", "list", equipmentId, shiftDate] as const,
  oee: (equipmentId: string, start: string, end: string) =>
    ["oee", equipmentId, start, end] as const,
};

// ─── Reasons ──────────────────────────────────────────────────────────

export function useReasons() {
  return useQuery({
    queryKey: KEYS.reasons,
    queryFn: fetchReasons,
  });
}

export function useCreateReason() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ReasonCreate) => createReason(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.reasons }),
  });
}

export function useUpdateReason() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: ReasonUpdate & { id: string }) => updateReason(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.reasons }),
  });
}

export function useDeleteReason() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteReason(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.reasons }),
  });
}

// ─── State Models ─────────────────────────────────────────────────────

export function useStateModels() {
  return useQuery({
    queryKey: KEYS.stateModels,
    queryFn: fetchStateModels,
  });
}

// ─── Equipment State Logs ─────────────────────────────────────────────

export function useEquipmentStates(equipmentId?: string) {
  return useQuery({
    queryKey: KEYS.stateList(equipmentId),
    queryFn: () => fetchEquipmentStates(equipmentId),
  });
}

export function useRecordStateChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StateChangeRequest) => recordStateChange(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.states }),
  });
}

// ─── Production Counters ──────────────────────────────────────────────

export function useCounters(equipmentId?: string, shiftDate?: string) {
  return useQuery({
    queryKey: KEYS.counterList(equipmentId, shiftDate),
    queryFn: () => fetchCounters(equipmentId, shiftDate),
  });
}

export function useCreateOrUpdateCounter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CounterCreateUpdate) => createOrUpdateCounter(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.counters }),
  });
}

// ─── OEE ──────────────────────────────────────────────────────────────

export function useOEE(
  equipmentId: string,
  periodStart: string,
  periodEnd: string,
  enabled = true,
) {
  return useQuery({
    queryKey: KEYS.oee(equipmentId, periodStart, periodEnd),
    queryFn: () => calculateOEE(equipmentId, periodStart, periodEnd),
    enabled,
  });
}
