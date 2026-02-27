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
  fetchWorkCenters,
  fetchWorkCenter,
  createWorkCenter,
  updateWorkCenter,
  fetchEquipment,
  createEquipment,
  updateEquipment,
  updateEquipmentStatus,
} from "../api/physicalModel";
import type { SiteCreate, SiteUpdate, AreaCreate, AreaUpdate, ProductionLineCreate, ProductionLineUpdate, WorkCenterCreate, WorkCenterUpdate, EquipmentCreate, EquipmentUpdate } from "../types";

const KEYS = {
  sites: ["sites"] as const,
  siteDetail: (id: string) => ["sites", id] as const,
  areas: (siteId: string) => ["areas", siteId] as const,
  areaDetail: (id: string) => ["area", id] as const,
  lines: (areaId: string) => ["lines", areaId] as const,
  lineDetail: (id: string) => ["line", id] as const,
  workCenters: (lineId: string) => ["workCenters", lineId] as const,
  workCenterDetail: (id: string) => ["workCenter", id] as const,
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

// ─── Work Centers ─────────────────────────────────────────────────────

export function useWorkCenters(lineId: string) {
  return useQuery({
    queryKey: KEYS.workCenters(lineId),
    queryFn: () => fetchWorkCenters(lineId),
    enabled: !!lineId,
  });
}

export function useWorkCenter(id: string) {
  return useQuery({
    queryKey: KEYS.workCenterDetail(id),
    queryFn: () => fetchWorkCenter(id),
    enabled: !!id,
  });
}

export function useCreateWorkCenter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ lineId, ...body }: WorkCenterCreate & { lineId: string }) =>
      createWorkCenter(lineId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workCenters"] }),
  });
}

export function useUpdateWorkCenter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkCenterUpdate & { id: string }) =>
      updateWorkCenter(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workCenters"] }),
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
