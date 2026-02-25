/**
 * TanStack Query hooks for Units of Measure.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUoMs,
  fetchUoM,
  createUoM,
  updateUoM,
  deleteUoM,
  convertUoM,
} from "../api/uom";
import type { UoMCreate, UoMUpdate, ConversionRequest } from "../types";

const KEYS = {
  all: ["uom"] as const,
  list: (type?: string) => [...KEYS.all, "list", type] as const,
  detail: (id: string) => [...KEYS.all, "detail", id] as const,
};

export function useUoMs(uomType?: string) {
  return useQuery({
    queryKey: KEYS.list(uomType),
    queryFn: () => fetchUoMs(uomType),
  });
}

export function useUoM(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => fetchUoM(id),
    enabled: !!id,
  });
}

export function useCreateUoM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UoMCreate) => createUoM(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateUoM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: UoMUpdate & { id: string }) => updateUoM(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteUoM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteUoM(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useConvertUoM() {
  return useMutation({
    mutationFn: (body: ConversionRequest) => convertUoM(body),
  });
}
