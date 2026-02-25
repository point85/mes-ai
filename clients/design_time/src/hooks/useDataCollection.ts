/**
 * TanStack Query hooks for Data Collection.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchDataDefinitions,
  createDataDefinition,
  updateDataDefinition,
  deleteDataDefinition,
  fetchDataPoints,
} from "../api/dataCollection";
import type { DataDefinitionCreate, DataDefinitionUpdate } from "../types";

const KEYS = {
  definitions: ["dataDefinitions"] as const,
  defList: (dataType?: string, source?: string) =>
    ["dataDefinitions", "list", dataType, source] as const,
  points: ["dataPoints"] as const,
  pointList: (defId?: string, unitId?: string) =>
    ["dataPoints", "list", defId, unitId] as const,
};

// ─── Data Definitions ─────────────────────────────────────────────────

export function useDataDefinitions(dataType?: string, source?: string) {
  return useQuery({
    queryKey: KEYS.defList(dataType, source),
    queryFn: () => fetchDataDefinitions(dataType, source),
  });
}

export function useCreateDataDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DataDefinitionCreate) => createDataDefinition(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.definitions }),
  });
}

export function useUpdateDataDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: DataDefinitionUpdate & { id: string }) =>
      updateDataDefinition(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.definitions }),
  });
}

export function useDeleteDataDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDataDefinition(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.definitions }),
  });
}

// ─── Data Points (read-only) ──────────────────────────────────────────

export function useDataPoints(definitionId?: string, unitId?: string) {
  return useQuery({
    queryKey: KEYS.pointList(definitionId, unitId),
    queryFn: () => fetchDataPoints(definitionId, unitId),
  });
}
