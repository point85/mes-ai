/**
 * TanStack Query hooks for Material Management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchMaterials,
  createMaterial,
  updateMaterial,
  deleteMaterial,
  fetchMaterialLots,
  createMaterialLot,
  updateMaterialLot,
} from "../api/material";
import type {
  MaterialCreate,
  MaterialUpdate,
  MaterialLotCreate,
  MaterialLotUpdate,
} from "../types";

const KEYS = {
  materials: ["materials"] as const,
  materialList: (type?: string) => ["materials", "list", type] as const,
  lots: ["materialLots"] as const,
  lotList: (materialId?: string, status?: string) =>
    ["materialLots", "list", materialId, status] as const,
};

// ─── Material Definitions ─────────────────────────────────────────────

export function useMaterials(materialType?: string) {
  return useQuery({
    queryKey: KEYS.materialList(materialType),
    queryFn: () => fetchMaterials(materialType),
  });
}

export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MaterialCreate) => createMaterial(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.materials }),
  });
}

export function useUpdateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: MaterialUpdate & { id: string }) =>
      updateMaterial(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.materials }),
  });
}

export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMaterial(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.materials }),
  });
}

// ─── Material Lots ────────────────────────────────────────────────────

export function useMaterialLots(materialId?: string, status?: string) {
  return useQuery({
    queryKey: KEYS.lotList(materialId, status),
    queryFn: () => fetchMaterialLots(materialId, status),
  });
}

export function useCreateMaterialLot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MaterialLotCreate) => createMaterialLot(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.lots }),
  });
}

export function useUpdateMaterialLot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: MaterialLotUpdate & { id: string }) =>
      updateMaterialLot(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.lots }),
  });
}
