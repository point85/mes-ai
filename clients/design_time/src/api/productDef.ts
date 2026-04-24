/**
 * Product Definition API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  Product,
  ProductCreate,
  ProductUpdate,
  BOM,
  BOMCreate,
  BOMUpdate,
  BOMItem,
  BOMItemCreate,
  BOMItemUpdate,
  ProcessRoute,
  RouteCreate,
  RouteUpdate,
  RouteStep,
  RouteStepCreate,
  RouteStepUpdate,
  StepParameter,
  StepParameterCreate,
  StepParameterUpdate,
  StepTransition,
  StepTransitionCreate,
  StepTransitionUpdate,
  RouteProductAssignment,
  RouteProductAssignmentCreate,
  RouteMaterialAssignment,
  RouteMaterialAssignmentCreate,
  Disposition,
  DispositionCreate,
  DispositionUpdate,
  StepEquipmentRequirement,
  StepEquipmentRequirementCreate,
  StepEquipmentRequirementUpdate,
  StepMaterialRequirement,
  StepMaterialRequirementCreate,
  StepMaterialRequirementUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Products ─────────────────────────────────────────────────────────

export async function fetchProducts(): Promise<ApiListResponse<Product>> {
  const { data } = await api.get<ApiListResponse<Product>>("/products", {
    params: { limit: "200" },
  });
  return data;
}

export async function fetchProduct(id: string): Promise<Product> {
  const { data } = await api.get<ApiResponse<Product>>(`/products/${id}`);
  return data.data;
}

export async function createProduct(body: ProductCreate): Promise<Product> {
  const { data } = await api.post<ApiResponse<Product>>("/products", body);
  return data.data;
}

export async function updateProduct(id: string, body: ProductUpdate): Promise<Product> {
  const { data } = await api.put<ApiResponse<Product>>(`/products/${id}`, body);
  return data.data;
}

export async function deleteProduct(id: string): Promise<void> {
  await api.delete(`/products/${id}`);
}

// ─── BOMs ─────────────────────────────────────────────────────────────

export async function fetchBOMs(productId: string): Promise<ApiListResponse<BOM>> {
  const { data } = await api.get<ApiListResponse<BOM>>(
    `/products/${productId}/boms`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchBOM(bomId: string): Promise<BOM> {
  const { data } = await api.get<ApiResponse<BOM>>(`/boms/${bomId}`);
  return data.data;
}

export async function createBOM(productId: string, body: BOMCreate): Promise<BOM> {
  const { data } = await api.post<ApiResponse<BOM>>(
    `/products/${productId}/boms`,
    body,
  );
  return data.data;
}

export async function updateBOM(bomId: string, body: BOMUpdate): Promise<BOM> {
  const { data } = await api.put<ApiResponse<BOM>>(`/boms/${bomId}`, body);
  return data.data;
}

export async function deleteBOM(bomId: string): Promise<void> {
  await api.delete(`/boms/${bomId}`);
}

// ─── BOM Items ────────────────────────────────────────────────────────

export async function fetchBOMItems(bomId: string): Promise<ApiListResponse<BOMItem>> {
  const { data } = await api.get<ApiListResponse<BOMItem>>(
    `/boms/${bomId}/items`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createBOMItem(bomId: string, body: BOMItemCreate): Promise<BOMItem> {
  const { data } = await api.post<ApiResponse<BOMItem>>(
    `/boms/${bomId}/items`,
    body,
  );
  return data.data;
}

export async function updateBOMItem(
  itemId: string,
  body: BOMItemUpdate,
): Promise<BOMItem> {
  const { data } = await api.put<ApiResponse<BOMItem>>(
    `/bom-items/${itemId}`,
    body,
  );
  return data.data;
}

export async function deleteBOMItem(itemId: string): Promise<void> {
  await api.delete(`/bom-items/${itemId}`);
}

// ─── Routes ───────────────────────────────────────────────────────────

export async function fetchRoutes(productId: string): Promise<ApiListResponse<ProcessRoute>> {
  const { data } = await api.get<ApiListResponse<ProcessRoute>>(
    `/products/${productId}/operations-definitions`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchRoute(routeId: string): Promise<ProcessRoute> {
  const { data } = await api.get<ApiResponse<ProcessRoute>>(`/operations-definitions/${routeId}`);
  return data.data;
}

export async function createRoute(productId: string, body: RouteCreate): Promise<ProcessRoute> {
  const { data } = await api.post<ApiResponse<ProcessRoute>>(
    `/products/${productId}/operations-definitions`,
    body,
  );
  return data.data;
}

export async function updateRoute(routeId: string, body: RouteUpdate): Promise<ProcessRoute> {
  const { data } = await api.put<ApiResponse<ProcessRoute>>(
    `/operations-definitions/${routeId}`,
    body,
  );
  return data.data;
}

// ─── Route Steps ──────────────────────────────────────────────────────

export async function fetchRouteSteps(routeId: string): Promise<ApiListResponse<RouteStep>> {
  const { data } = await api.get<ApiListResponse<RouteStep>>(
    `/operations-definitions/${routeId}/process-segments`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createRouteStep(
  routeId: string,
  body: RouteStepCreate,
): Promise<RouteStep> {
  const { data } = await api.post<ApiResponse<RouteStep>>(
    `/operations-definitions/${routeId}/process-segments`,
    body,
  );
  return data.data;
}

export async function updateRouteStep(
  stepId: string,
  body: RouteStepUpdate,
): Promise<RouteStep> {
  const { data } = await api.put<ApiResponse<RouteStep>>(
    `/process-segments/${stepId}`,
    body,
  );
  return data.data;
}

// ─── Step Parameters ──────────────────────────────────────────────────

export async function fetchStepParameters(
  stepId: string,
): Promise<ApiListResponse<StepParameter>> {
  const { data } = await api.get<ApiListResponse<StepParameter>>(
    `/process-segments/${stepId}/parameters`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createStepParameter(
  stepId: string,
  body: StepParameterCreate,
): Promise<StepParameter> {
  const { data } = await api.post<ApiResponse<StepParameter>>(
    `/process-segments/${stepId}/parameters`,
    body,
  );
  return data.data;
}

export async function updateStepParameter(
  paramId: string,
  body: StepParameterUpdate,
): Promise<StepParameter> {
  const { data } = await api.put<ApiResponse<StepParameter>>(
    `/segment-parameters/${paramId}`,
    body,
  );
  return data.data;
}

export async function deleteStepParameter(paramId: string): Promise<void> {
  await api.delete(`/segment-parameters/${paramId}`);
}

// ─── Step Transitions ─────────────────────────────────────────────────

export async function fetchStepTransitions(
  stepId: string,
): Promise<ApiListResponse<StepTransition>> {
  const { data } = await api.get<ApiListResponse<StepTransition>>(
    `/process-segments/${stepId}/dependencies`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createStepTransition(
  stepId: string,
  body: StepTransitionCreate,
): Promise<StepTransition> {
  const { data } = await api.post<ApiResponse<StepTransition>>(
    `/process-segments/${stepId}/dependencies`,
    body,
  );
  return data.data;
}

export async function updateStepTransition(
  transitionId: string,
  body: StepTransitionUpdate,
): Promise<StepTransition> {
  const { data } = await api.put<ApiResponse<StepTransition>>(
    `/process-segment-dependencies/${transitionId}`,
    body,
  );
  return data.data;
}

export async function deleteStepTransition(transitionId: string): Promise<void> {
  await api.delete(`/process-segment-dependencies/${transitionId}`);
}

// ─── Standalone Routes (Route Editor) ─────────────────────────────────

export async function fetchAllRoutes(): Promise<ApiListResponse<ProcessRoute>> {
  const { data } = await api.get<ApiListResponse<ProcessRoute>>("/operations-definitions", {
    params: { limit: "200" },
  });
  return data;
}

export async function createStandaloneRoute(body: RouteCreate): Promise<ProcessRoute> {
  const { data } = await api.post<ApiResponse<ProcessRoute>>("/operations-definitions", body);
  return data.data;
}

// ─── Route–Product Assignments ────────────────────────────────────────

export async function fetchRouteProducts(
  routeId: string,
): Promise<ApiListResponse<RouteProductAssignment>> {
  const { data } = await api.get<ApiListResponse<RouteProductAssignment>>(
    `/operations-definitions/${routeId}/products`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function assignProductToRoute(
  routeId: string,
  body: RouteProductAssignmentCreate,
): Promise<RouteProductAssignment> {
  const { data } = await api.post<ApiResponse<RouteProductAssignment>>(
    `/operations-definitions/${routeId}/products`,
    body,
  );
  return data.data;
}

export async function unassignProductFromRoute(
  routeId: string,
  productId: string,
): Promise<void> {
  await api.delete(`/operations-definitions/${routeId}/products/${productId}`);
}

// ─── Route Update / Delete ────────────────────────────────────────────

export async function updateStandaloneRoute(id: string, body: RouteUpdate): Promise<ProcessRoute> {
  const { data } = await api.put<ApiResponse<ProcessRoute>>(`/operations-definitions/${id}`, body);
  return data.data;
}

export async function deleteRoute(routeId: string): Promise<void> {
  await api.delete(`/operations-definitions/${routeId}`);
}

export async function deleteStep(stepId: string): Promise<void> {
  await api.delete(`/process-segments/${stepId}`);
}

// ─── Route–Material Assignments ───────────────────────────────────────

export async function fetchRouteMaterials(
  routeId: string,
): Promise<ApiListResponse<RouteMaterialAssignment>> {
  const { data } = await api.get<ApiListResponse<RouteMaterialAssignment>>(
    `/operations-definitions/${routeId}/materials`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function assignMaterialToRoute(
  routeId: string,
  body: RouteMaterialAssignmentCreate,
): Promise<RouteMaterialAssignment> {
  const { data } = await api.post<ApiResponse<RouteMaterialAssignment>>(
    `/operations-definitions/${routeId}/materials`,
    body,
  );
  return data.data;
}

export async function unassignMaterialFromRoute(
  routeId: string,
  materialId: string,
): Promise<void> {
  await api.delete(`/operations-definitions/${routeId}/materials/${materialId}`);
}

// ─── Dispositions ─────────────────────────────────────────────────────

export async function fetchDispositions(): Promise<ApiListResponse<Disposition>> {
  const { data } = await api.get<ApiListResponse<Disposition>>("/dispositions", {
    params: { limit: "200" },
  });
  return data;
}

export async function createDisposition(body: DispositionCreate): Promise<Disposition> {
  const { data } = await api.post<ApiResponse<Disposition>>("/dispositions", body);
  return data.data;
}

export async function updateDisposition(id: string, body: DispositionUpdate): Promise<Disposition> {
  const { data } = await api.put<ApiResponse<Disposition>>(`/dispositions/${id}`, body);
  return data.data;
}

export async function deleteDisposition(id: string): Promise<void> {
  await api.delete(`/dispositions/${id}`);
}

// ─── Step Equipment Requirements (ISA-95 Process Segment) ─────────────

export async function fetchStepEquipmentRequirements(
  stepId: string,
): Promise<ApiListResponse<StepEquipmentRequirement>> {
  const { data } = await api.get<ApiListResponse<StepEquipmentRequirement>>(
    `/process-segments/${stepId}/equipment-requirements`,
  );
  return data;
}

export async function createStepEquipmentRequirement(
  stepId: string,
  body: StepEquipmentRequirementCreate,
): Promise<StepEquipmentRequirement> {
  const { data } = await api.post<ApiResponse<StepEquipmentRequirement>>(
    `/process-segments/${stepId}/equipment-requirements`,
    body,
  );
  return data.data;
}

export async function updateStepEquipmentRequirement(
  requirementId: string,
  body: StepEquipmentRequirementUpdate,
): Promise<StepEquipmentRequirement> {
  const { data } = await api.patch<ApiResponse<StepEquipmentRequirement>>(
    `/segment-equipment-requirements/${requirementId}`,
    body,
  );
  return data.data;
}

export async function deleteStepEquipmentRequirement(
  requirementId: string,
): Promise<void> {
  await api.delete(`/segment-equipment-requirements/${requirementId}`);
}

// ─── Step Material Requirements (ISA-95 Process Segment) ───────────────

export async function fetchStepMaterialRequirements(
  stepId: string,
): Promise<ApiListResponse<StepMaterialRequirement>> {
  const { data } = await api.get<ApiListResponse<StepMaterialRequirement>>(
    `/process-segments/${stepId}/material-requirements`,
  );
  return data;
}

export async function createStepMaterialRequirement(
  stepId: string,
  body: StepMaterialRequirementCreate,
): Promise<StepMaterialRequirement> {
  const { data } = await api.post<ApiResponse<StepMaterialRequirement>>(
    `/process-segments/${stepId}/material-requirements`,
    body,
  );
  return data.data;
}

export async function updateStepMaterialRequirement(
  requirementId: string,
  body: StepMaterialRequirementUpdate,
): Promise<StepMaterialRequirement> {
  const { data } = await api.patch<ApiResponse<StepMaterialRequirement>>(
    `/segment-material-requirements/${requirementId}`,
    body,
  );
  return data.data;
}

export async function deleteStepMaterialRequirement(
  requirementId: string,
): Promise<void> {
  await api.delete(`/segment-material-requirements/${requirementId}`);
}
