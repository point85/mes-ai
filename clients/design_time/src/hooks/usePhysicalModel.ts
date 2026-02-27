/**
 * TanStack Query hooks for Physical Model (Sites → Areas → Lines → WC → Equipment).
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchSites,
  fetchSite,
  createSite,
  updateSite,
  deleteSite,
  fetchAreas,
  fetchArea,
  createArea,
  updateArea,
  fetchLines,
  fetchLine,
  createLine,
  updateLine,
  fetchWorkCells,
  fetchWorkCell,
  createWorkCell,
  updateWorkCell,
  fetchEquipment,
  createEquipment,
  updateEquipment,
  updateEquipmentStatus,
} from "../api/physicalModel";
import type { SiteCreate, SiteUpdate, AreaCreate, AreaUpdate, ProductionLineCreate, ProductionLineUpdate, WorkCellCreate, WorkCellUpdate, EquipmentCreate, EquipmentUpdate } from "../types";

const KEYS = {
  sites: ["sites"] as const,
  siteDetail: (id: string) => ["sites", id] as const,
  areas: (siteId: string) => ["areas", siteId] as const,
  areaDetail: (id: string) => ["area", id] as const,
  lines: (areaId: string) => ["lines", areaId] as const,
  lineDetail: (id: string) => ["line", id] as const,
  workCells: (lineId: string) => ["workCells", lineId] as const,
  workCellDetail: (id: string) => ["workCell", id] as const,
  equipment: (wcId: string) => ["equipment", wcId] as const,
};

// ─── Sites ────────────────────────────────────────────────────────────

export function useSites() {
  return useQuery({ queryKey: KEYS.sites, queryFn: fetchSites });
}

export function useSite(id: string) {
  return useQuery({
    queryKey: KEYS.siteDetail(id),
    queryFn: () => fetchSite(id),
    enabled: !!id,
  });
}

export function useCreateSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SiteCreate) => createSite(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.sites }),
  });
}

export function useUpdateSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: SiteUpdate & { id: string }) => updateSite(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.sites }),
  });
}

export function useDeleteSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSite(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.sites }),
  });
}

// ─── Areas ────────────────────────────────────────────────────────────

export function useAreas(siteId: string) {
  return useQuery({
    queryKey: KEYS.areas(siteId),
    queryFn: () => fetchAreas(siteId),
    enabled: !!siteId,
  });
}

export function useArea(id: string) {
  return useQuery({
    queryKey: KEYS.areaDetail(id),
    queryFn: () => fetchArea(id),
    enabled: !!id,
  });
}

export function useCreateArea() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ siteId, ...body }: AreaCreate & { siteId: string }) =>
      createArea(siteId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["areas"] }),
  });
}

export function useUpdateArea() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: AreaUpdate & { id: string }) => updateArea(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["areas"] }),
  });
}

// ─── Lines ────────────────────────────────────────────────────────────

export function useLines(areaId: string) {
  return useQuery({
    queryKey: KEYS.lines(areaId),
    queryFn: () => fetchLines(areaId),
    enabled: !!areaId,
  });
}

export function useLine(id: string) {
  return useQuery({
    queryKey: KEYS.lineDetail(id),
    queryFn: () => fetchLine(id),
    enabled: !!id,
  });
}

export function useCreateLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ areaId, ...body }: ProductionLineCreate & { areaId: string }) =>
      createLine(areaId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lines"] }),
  });
}

export function useUpdateLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: ProductionLineUpdate & { id: string }) =>
      updateLine(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lines"] }),
  });
}

// ─── Work Cells ─────────────────────────────────────────────────────

export function useWorkCells(lineId: string) {
  return useQuery({
    queryKey: KEYS.workCells(lineId),
    queryFn: () => fetchWorkCells(lineId),
    enabled: !!lineId,
  });
}

export function useWorkCell(id: string) {
  return useQuery({
    queryKey: KEYS.workCellDetail(id),
    queryFn: () => fetchWorkCell(id),
    enabled: !!id,
  });
}

export function useCreateWorkCell() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ lineId, ...body }: WorkCellCreate & { lineId: string }) =>
      createWorkCell(lineId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workCells"] }),
  });
}

export function useUpdateWorkCell() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkCellUpdate & { id: string }) =>
      updateWorkCell(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workCells"] }),
  });
}

// ─── Equipment ────────────────────────────────────────────────────────

export function useEquipment(wcId: string) {
  return useQuery({
    queryKey: KEYS.equipment(wcId),
    queryFn: () => fetchEquipment(wcId),
    enabled: !!wcId,
  });
}

export function useCreateEquipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ wcId, ...body }: EquipmentCreate & { wcId: string }) =>
      createEquipment(wcId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipment"] }),
  });
}

export function useUpdateEquipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: EquipmentUpdate & { id: string }) =>
      updateEquipment(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipment"] }),
  });
}

export function useUpdateEquipmentStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: string;
      status: string;
      reason?: string;
    }) => updateEquipmentStatus(id, status, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipment"] }),
  });
}
