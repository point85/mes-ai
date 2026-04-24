/**
 * TanStack Query hooks for Product Definition.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  fetchBOMs,
  createBOM,
  updateBOM,
  deleteBOM,
  fetchBOMItems,
  createBOMItem,
  updateBOMItem,
  deleteBOMItem,
  fetchRoutes,
  createRoute,
  updateRoute,
  fetchRouteSteps,
  createRouteStep,
  updateRouteStep,
  fetchStepParameters,
  createStepParameter,
  updateStepParameter,
  deleteStepParameter,
  fetchStepTransitions,
  createStepTransition,
  updateStepTransition,
  deleteStepTransition,
  fetchAllRoutes,
  createStandaloneRoute,
  updateStandaloneRoute,
  deleteRoute,
  deleteStep,
  fetchRouteProducts,
  assignProductToRoute,
  unassignProductFromRoute,
  fetchRouteMaterials,
  assignMaterialToRoute,
  unassignMaterialFromRoute,
  fetchDispositions,
  createDisposition,
  updateDisposition,
  deleteDisposition,
  fetchStepEquipmentRequirements,
  createStepEquipmentRequirement,
  updateStepEquipmentRequirement,
  deleteStepEquipmentRequirement,
} from "../api/productDef";
import type {
  ProductCreate,
  ProductUpdate,
  BOMCreate,
  BOMUpdate,
  BOMItemCreate,
  BOMItemUpdate,
  RouteCreate,
  RouteUpdate,
  RouteStepCreate,
  RouteStepUpdate,
  StepParameterCreate,
  StepParameterUpdate,
  StepTransitionCreate,
  StepTransitionUpdate,
  RouteProductAssignmentCreate,
  RouteMaterialAssignmentCreate,
  DispositionCreate,
  DispositionUpdate,
  StepEquipmentRequirementCreate,
  StepEquipmentRequirementUpdate,
} from "../types";

const KEYS = {
  products: ["products"] as const,
  boms: (productId: string) => ["boms", productId] as const,
  bomItems: (bomId: string) => ["bomItems", bomId] as const,
  routes: (productId: string) => ["routes", productId] as const,
  allRoutes: ["allRoutes"] as const,
  routeProducts: (routeId: string) => ["routeProducts", routeId] as const,
  routeMaterials: (routeId: string) => ["routeMaterials", routeId] as const,
  steps: (routeId: string) => ["steps", routeId] as const,
  params: (stepId: string) => ["stepParams", stepId] as const,
  transitions: (stepId: string) => ["stepTransitions", stepId] as const,
  dispositions: ["dispositions"] as const,
  stepEquipReqs: (stepId: string) => ["stepEquipReqs", stepId] as const,
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

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProduct(id),
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

export function useDeleteBOM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteBOM(id),
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

export function useUpdateBOMItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: BOMItemUpdate & { id: string }) =>
      updateBOMItem(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bomItems"] }),
  });
}

export function useDeleteBOMItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteBOMItem(id),
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

export function useUpdateStepParameter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: StepParameterUpdate & { id: string }) =>
      updateStepParameter(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stepParams"] }),
  });
}

export function useDeleteStepParameter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteStepParameter(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stepParams"] }),
  });
}

// ─── Step Transitions ─────────────────────────────────────────────────

export function useStepTransitions(stepId: string) {
  return useQuery({
    queryKey: KEYS.transitions(stepId),
    queryFn: () => fetchStepTransitions(stepId),
    enabled: !!stepId,
  });
}

export function useCreateStepTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stepId, ...body }: StepTransitionCreate & { stepId: string }) =>
      createStepTransition(stepId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stepTransitions"] }),
  });
}

export function useUpdateStepTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: StepTransitionUpdate & { id: string }) =>
      updateStepTransition(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stepTransitions"] }),
  });
}

export function useDeleteStepTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteStepTransition(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stepTransitions"] }),
  });
}

// ─── Standalone Routes (Route Editor) ─────────────────────────────────

export function useAllRoutes() {
  return useQuery({ queryKey: KEYS.allRoutes, queryFn: fetchAllRoutes });
}

export function useCreateStandaloneRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RouteCreate) => createStandaloneRoute(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.allRoutes });
      qc.invalidateQueries({ queryKey: ["routes"] });
    },
  });
}

// ─── Route–Product Assignments ────────────────────────────────────────

export function useRouteProducts(routeId: string) {
  return useQuery({
    queryKey: KEYS.routeProducts(routeId),
    queryFn: () => fetchRouteProducts(routeId),
    enabled: !!routeId,
  });
}

export function useAssignProductToRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ routeId, ...body }: RouteProductAssignmentCreate & { routeId: string }) =>
      assignProductToRoute(routeId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routeProducts"] }),
  });
}

export function useUnassignProductFromRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ routeId, productId }: { routeId: string; productId: string }) =>
      unassignProductFromRoute(routeId, productId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routeProducts"] }),
  });
}

// ─── Standalone Route Update / Delete ─────────────────────────────────

export function useUpdateStandaloneRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: RouteUpdate & { id: string }) =>
      updateStandaloneRoute(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.allRoutes });
      qc.invalidateQueries({ queryKey: ["routes"] });
    },
  });
}

export function useDeleteRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (routeId: string) => deleteRoute(routeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.allRoutes });
      qc.invalidateQueries({ queryKey: ["routes"] });
    },
  });
}

export function useDeleteStep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) => deleteStep(stepId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["steps"] }),
  });
}

// ─── Route–Material Assignments ───────────────────────────────────────

export function useRouteMaterials(routeId: string) {
  return useQuery({
    queryKey: KEYS.routeMaterials(routeId),
    queryFn: () => fetchRouteMaterials(routeId),
    enabled: !!routeId,
  });
}

export function useAssignMaterialToRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ routeId, ...body }: RouteMaterialAssignmentCreate & { routeId: string }) =>
      assignMaterialToRoute(routeId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routeMaterials"] }),
  });
}

export function useUnassignMaterialFromRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ routeId, materialId }: { routeId: string; materialId: string }) =>
      unassignMaterialFromRoute(routeId, materialId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routeMaterials"] }),
  });
}

// ─── Dispositions ─────────────────────────────────────────────────────

export function useDispositions() {
  return useQuery({ queryKey: KEYS.dispositions, queryFn: fetchDispositions });
}

export function useCreateDisposition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DispositionCreate) => createDisposition(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.dispositions }),
  });
}

export function useUpdateDisposition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: DispositionUpdate & { id: string }) =>
      updateDisposition(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.dispositions }),
  });
}

export function useDeleteDisposition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDisposition(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.dispositions }),
  });
}

// ─── Step Equipment Requirements ─────────────────────────────────────

export function useStepEquipmentRequirements(stepId: string | undefined) {
  return useQuery({
    queryKey: stepId ? KEYS.stepEquipReqs(stepId) : ["stepEquipReqs", "none"],
    queryFn: () => fetchStepEquipmentRequirements(stepId as string),
    enabled: !!stepId,
  });
}

export function useCreateStepEquipmentRequirement(stepId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StepEquipmentRequirementCreate) =>
      createStepEquipmentRequirement(stepId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.stepEquipReqs(stepId) }),
  });
}

export function useUpdateStepEquipmentRequirement(stepId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: StepEquipmentRequirementUpdate & { id: string }) =>
      updateStepEquipmentRequirement(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.stepEquipReqs(stepId) }),
  });
}

export function useDeleteStepEquipmentRequirement(stepId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteStepEquipmentRequirement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.stepEquipReqs(stepId) }),
  });
}
