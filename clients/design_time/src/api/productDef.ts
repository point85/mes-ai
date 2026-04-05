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
  ProcessRoute,
  RouteCreate,
  RouteUpdate,
  RouteStep,
  RouteStepCreate,
  RouteStepUpdate,
  StepParameter,
  StepParameterCreate,
  StepTransition,
  StepTransitionCreate,
  StepTransitionUpdate,
  RouteProductAssignment,
  RouteProductAssignmentCreate,
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

// ─── Routes ───────────────────────────────────────────────────────────

export async function fetchRoutes(productId: string): Promise<ApiListResponse<ProcessRoute>> {
  const { data } = await api.get<ApiListResponse<ProcessRoute>>(
    `/products/${productId}/routes`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchRoute(routeId: string): Promise<ProcessRoute> {
  const { data } = await api.get<ApiResponse<ProcessRoute>>(`/routes/${routeId}`);
  return data.data;
}

export async function createRoute(productId: string, body: RouteCreate): Promise<ProcessRoute> {
  const { data } = await api.post<ApiResponse<ProcessRoute>>(
    `/products/${productId}/routes`,
    body,
  );
  return data.data;
}

export async function updateRoute(routeId: string, body: RouteUpdate): Promise<ProcessRoute> {
  const { data } = await api.put<ApiResponse<ProcessRoute>>(
    `/routes/${routeId}`,
    body,
  );
  return data.data;
}

// ─── Route Steps ──────────────────────────────────────────────────────

export async function fetchRouteSteps(routeId: string): Promise<ApiListResponse<RouteStep>> {
  const { data } = await api.get<ApiListResponse<RouteStep>>(
    `/routes/${routeId}/steps`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createRouteStep(
  routeId: string,
  body: RouteStepCreate,
): Promise<RouteStep> {
  const { data } = await api.post<ApiResponse<RouteStep>>(
    `/routes/${routeId}/steps`,
    body,
  );
  return data.data;
}

export async function updateRouteStep(
  stepId: string,
  body: RouteStepUpdate,
): Promise<RouteStep> {
  const { data } = await api.put<ApiResponse<RouteStep>>(
    `/steps/${stepId}`,
    body,
  );
  return data.data;
}

// ─── Step Parameters ──────────────────────────────────────────────────

export async function fetchStepParameters(
  stepId: string,
): Promise<ApiListResponse<StepParameter>> {
  const { data } = await api.get<ApiListResponse<StepParameter>>(
    `/steps/${stepId}/parameters`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createStepParameter(
  stepId: string,
  body: StepParameterCreate,
): Promise<StepParameter> {
  const { data } = await api.post<ApiResponse<StepParameter>>(
    `/steps/${stepId}/parameters`,
    body,
  );
  return data.data;
}

// ─── Step Transitions ─────────────────────────────────────────────────

export async function fetchStepTransitions(
  stepId: string,
): Promise<ApiListResponse<StepTransition>> {
  const { data } = await api.get<ApiListResponse<StepTransition>>(
    `/steps/${stepId}/transitions`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createStepTransition(
  stepId: string,
  body: StepTransitionCreate,
): Promise<StepTransition> {
  const { data } = await api.post<ApiResponse<StepTransition>>(
    `/steps/${stepId}/transitions`,
    body,
  );
  return data.data;
}

export async function updateStepTransition(
  transitionId: string,
  body: StepTransitionUpdate,
): Promise<StepTransition> {
  const { data } = await api.put<ApiResponse<StepTransition>>(
    `/transitions/${transitionId}`,
    body,
  );
  return data.data;
}

export async function deleteStepTransition(transitionId: string): Promise<void> {
  await api.delete(`/transitions/${transitionId}`);
}

// ─── Standalone Routes (Route Editor) ─────────────────────────────────

export async function fetchAllRoutes(): Promise<ApiListResponse<ProcessRoute>> {
  const { data } = await api.get<ApiListResponse<ProcessRoute>>("/routes", {
    params: { limit: "200" },
  });
  return data;
}

export async function createStandaloneRoute(body: RouteCreate): Promise<ProcessRoute> {
  const { data } = await api.post<ApiResponse<ProcessRoute>>("/routes", body);
  return data.data;
}

// ─── Route–Product Assignments ────────────────────────────────────────

export async function fetchRouteProducts(
  routeId: string,
): Promise<ApiListResponse<RouteProductAssignment>> {
  const { data } = await api.get<ApiListResponse<RouteProductAssignment>>(
    `/routes/${routeId}/products`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function assignProductToRoute(
  routeId: string,
  body: RouteProductAssignmentCreate,
): Promise<RouteProductAssignment> {
  const { data } = await api.post<ApiResponse<RouteProductAssignment>>(
    `/routes/${routeId}/products`,
    body,
  );
  return data.data;
}

export async function unassignProductFromRoute(
  routeId: string,
  productId: string,
): Promise<void> {
  await api.delete(`/routes/${routeId}/products/${productId}`);
}
