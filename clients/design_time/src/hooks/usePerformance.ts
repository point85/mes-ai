/**
 * TanStack Query hooks for Performance Analysis.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchEquipmentStates,
  recordStateChange,
  fetchCounters,
  createOrUpdateCounter,
  calculateOEE,
} from "../api/performance";
import type { StateChangeRequest, CounterCreateUpdate } from "../types";

const KEYS = {
  states: ["equipmentStates"] as const,
  stateList: (equipmentId?: string) =>
    ["equipmentStates", "list", equipmentId] as const,
  counters: ["productionCounters"] as const,
  counterList: (equipmentId?: string, shiftDate?: string) =>
    ["productionCounters", "list", equipmentId, shiftDate] as const,
  oee: (equipmentId: string, start: string, end: string) =>
    ["oee", equipmentId, start, end] as const,
};

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
