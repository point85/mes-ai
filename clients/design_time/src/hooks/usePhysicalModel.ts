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
  fetchAllLines,
  fetchLines,
  fetchLine,
  createLine,
  updateLine,
  fetchWorkCells,
  fetchAllWorkCells,
  fetchWorkCell,
  createWorkCell,
  updateWorkCell,
  fetchAllEquipment,
  fetchEquipment,
  createEquipment,
  updateEquipment,
  fetchEquipmentMaterials,
  createEquipmentMaterial,
  updateEquipmentMaterial,
  deleteEquipmentMaterial,
  fetchEquipmentClasses,
  fetchEquipmentClassDetail,
  createEquipmentClass,
  updateEquipmentClass,
  deleteEquipmentClass,
  fetchClassProperties,
  createClassProperty,
  updateClassProperty,
  deleteClassProperty,
  fetchEquipmentCapabilities,
  createEquipmentCapability,
  deleteEquipmentCapability,
} from "../api/physicalModel";
import type { SiteCreate, SiteUpdate, AreaCreate, AreaUpdate, ProductionLineCreate, ProductionLineUpdate, WorkCellCreate, WorkCellUpdate, EquipmentCreate, EquipmentUpdate, EquipmentMaterialCreate, EquipmentMaterialUpdate, EquipmentCapabilityCreate, EquipmentClassCreate, EquipmentClassUpdate, EquipmentClassPropertyCreate, EquipmentClassPropertyUpdate } from "../types";

const KEYS = {
  sites: ["sites"] as const,
  siteDetail: (id: string) => ["sites", id] as const,
  areas: (siteId: string) => ["areas", siteId] as const,
  areaDetail: (id: string) => ["area", id] as const,
  lines: (areaId: string) => ["lines", areaId] as const,
  allLines: ["lines", "all"] as const,
  lineDetail: (id: string) => ["line", id] as const,
  workCells: (lineId: string) => ["workCells", lineId] as const,
  allWorkCells: ["workCells", "all"] as const,
  workCellDetail: (id: string) => ["workCell", id] as const,
  equipment: (wcId: string) => ["equipment", wcId] as const,
  allEquipment: ["equipment", "all"] as const,
  equipmentMaterials: (equipId: string) => ["equipmentMaterials", equipId] as const,
  equipmentClasses: ["equipmentClasses"] as const,
  equipmentClassDetail: (id: string) => ["equipmentClasses", id] as const,
  classProperties: (classId: string) => ["classProperties", classId] as const,
  equipmentCapabilities: (equipId: string) => ["equipmentCapabilities", equipId] as const,
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
export function useAllLines() {
  return useQuery({
    queryKey: KEYS.allLines,
    queryFn: fetchAllLines,
  });
}
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

export function useAllWorkCells() {
  return useQuery({
    queryKey: KEYS.allWorkCells,
    queryFn: fetchAllWorkCells,
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

export function useAllEquipment() {
  return useQuery({
    queryKey: KEYS.allEquipment,
    queryFn: fetchAllEquipment,
  });
}

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


// ─── Equipment–Material Setups ─────────────────────────────────────

export function useEquipmentMaterials(equipId: string) {
  return useQuery({
    queryKey: KEYS.equipmentMaterials(equipId),
    queryFn: () => fetchEquipmentMaterials(equipId),
    enabled: !!equipId,
  });
}

export function useCreateEquipmentMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ equipId, ...body }: EquipmentMaterialCreate & { equipId: string }) =>
      createEquipmentMaterial(equipId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipmentMaterials"] }),
  });
}

export function useUpdateEquipmentMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: EquipmentMaterialUpdate & { id: string }) =>
      updateEquipmentMaterial(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipmentMaterials"] }),
  });
}

export function useDeleteEquipmentMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteEquipmentMaterial(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipmentMaterials"] }),
  });
}


// ─── Equipment Classes (ISA-95 Part 2) ─────────────────────────────

export function useEquipmentClasses() {
  return useQuery({
    queryKey: KEYS.equipmentClasses,
    queryFn: fetchEquipmentClasses,
  });
}

export function useEquipmentClassDetail(classId: string) {
  return useQuery({
    queryKey: KEYS.equipmentClassDetail(classId),
    queryFn: () => fetchEquipmentClassDetail(classId),
    enabled: !!classId,
  });
}

export function useCreateEquipmentClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EquipmentClassCreate) => createEquipmentClass(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.equipmentClasses }),
  });
}

export function useUpdateEquipmentClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: EquipmentClassUpdate & { id: string }) =>
      updateEquipmentClass(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.equipmentClasses }),
  });
}

export function useDeleteEquipmentClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteEquipmentClass(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.equipmentClasses }),
  });
}

export function useClassProperties(classId: string) {
  return useQuery({
    queryKey: KEYS.classProperties(classId),
    queryFn: () => fetchClassProperties(classId),
    enabled: !!classId,
  });
}

export function useCreateClassProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, ...body }: EquipmentClassPropertyCreate & { classId: string }) =>
      createClassProperty(classId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classProperties"] }),
  });
}

export function useUpdateClassProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: EquipmentClassPropertyUpdate & { id: string }) =>
      updateClassProperty(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classProperties"] }),
  });
}

export function useDeleteClassProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteClassProperty(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classProperties"] }),
  });
}


// ─── Equipment Capabilities (ISA-95 Part 2) ────────────────────────

export function useEquipmentCapabilities(equipId: string) {
  return useQuery({
    queryKey: KEYS.equipmentCapabilities(equipId),
    queryFn: () => fetchEquipmentCapabilities(equipId),
    enabled: !!equipId,
  });
}

export function useCreateEquipmentCapability() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ equipId, ...body }: EquipmentCapabilityCreate & { equipId: string }) =>
      createEquipmentCapability(equipId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipmentCapabilities"] }),
  });
}

export function useDeleteEquipmentCapability() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (capId: string) => deleteEquipmentCapability(capId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipmentCapabilities"] }),
  });
}
