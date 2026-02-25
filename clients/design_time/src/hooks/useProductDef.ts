/**
 * TanStack Query hooks for Product Definition.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchProducts,
  createProduct,
  updateProduct,
  fetchBOMs,
  createBOM,
  updateBOM,
  fetchBOMItems,
  createBOMItem,
  fetchRoutes,
  createRoute,
  updateRoute,
  fetchRouteSteps,
  createRouteStep,
  updateRouteStep,
  fetchStepParameters,
  createStepParameter,
} from "../api/productDef";
import type {
  ProductCreate,
  ProductUpdate,
  BOMCreate,
  BOMUpdate,
  BOMItemCreate,
  RouteCreate,
  RouteUpdate,
  RouteStepCreate,
  RouteStepUpdate,
  StepParameterCreate,
} from "../types";

const KEYS = {
  products: ["products"] as const,
  boms: (productId: string) => ["boms", productId] as const,
  bomItems: (bomId: string) => ["bomItems", bomId] as const,
  routes: (productId: string) => ["routes", productId] as const,
  steps: (routeId: string) => ["steps", routeId] as const,
  params: (stepId: string) => ["stepParams", stepId] as const,
};

// ─── Products ─────────────────────────────────────────────────────────

export function useProducts() {
  return useQuery({ queryKey: KEYS.products, queryFn: fetchProducts });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProductCreate) => createProduct(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.products }),
  });
}

export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: ProductUpdate & { id: string }) =>
      updateProduct(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.products }),
  });
}

// ─── BOMs ─────────────────────────────────────────────────────────────

export function useBOMs(productId: string) {
  return useQuery({
    queryKey: KEYS.boms(productId),
    queryFn: () => fetchBOMs(productId),
    enabled: !!productId,
  });
}

export function useCreateBOM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, ...body }: BOMCreate & { productId: string }) =>
      createBOM(productId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boms"] }),
  });
}

export function useUpdateBOM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: BOMUpdate & { id: string }) => updateBOM(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boms"] }),
  });
}

// ─── BOM Items ────────────────────────────────────────────────────────

export function useBOMItems(bomId: string) {
  return useQuery({
    queryKey: KEYS.bomItems(bomId),
    queryFn: () => fetchBOMItems(bomId),
    enabled: !!bomId,
  });
}

export function useCreateBOMItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ bomId, ...body }: BOMItemCreate & { bomId: string }) =>
      createBOMItem(bomId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bomItems"] }),
  });
}

// ─── Routes ───────────────────────────────────────────────────────────

export function useRoutes(productId: string) {
  return useQuery({
    queryKey: KEYS.routes(productId),
    queryFn: () => fetchRoutes(productId),
    enabled: !!productId,
  });
}

export function useCreateRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, ...body }: RouteCreate & { productId: string }) =>
      createRoute(productId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routes"] }),
  });
}

export function useUpdateRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: RouteUpdate & { id: string }) =>
      updateRoute(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routes"] }),
  });
}

// ─── Route Steps ──────────────────────────────────────────────────────

export function useRouteSteps(routeId: string) {
  return useQuery({
    queryKey: KEYS.steps(routeId),
    queryFn: () => fetchRouteSteps(routeId),
    enabled: !!routeId,
  });
}

export function useCreateRouteStep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ routeId, ...body }: RouteStepCreate & { routeId: string }) =>
      createRouteStep(routeId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["steps"] }),
  });
}

export function useUpdateRouteStep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: RouteStepUpdate & { id: string }) =>
      updateRouteStep(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["steps"] }),
  });
}

// ─── Step Parameters ──────────────────────────────────────────────────

export function useStepParameters(stepId: string) {
  return useQuery({
    queryKey: KEYS.params(stepId),
    queryFn: () => fetchStepParameters(stepId),
    enabled: !!stepId,
  });
}

export function useCreateStepParameter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stepId, ...body }: StepParameterCreate & { stepId: string }) =>
      createStepParameter(stepId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stepParams"] }),
  });
}
