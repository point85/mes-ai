/**
 * Production Order API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  ProductionOrder,
  OrderCreate,
  OrderUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

export async function fetchOrders(
  status?: string,
  productId?: string,
): Promise<ApiListResponse<ProductionOrder>> {
  const params: Record<string, string> = { limit: "200" };
  if (status) params.status = status;
  if (productId) params.product_id = productId;
  const { data } = await api.get<ApiListResponse<ProductionOrder>>("/orders", {
    params,
  });
  return data;
}

export async function fetchOrder(id: string): Promise<ProductionOrder> {
  const { data } = await api.get<ApiResponse<ProductionOrder>>(`/orders/${id}`);
  return data.data;
}

export async function createOrder(body: OrderCreate): Promise<ProductionOrder> {
  const { data } = await api.post<ApiResponse<ProductionOrder>>("/orders", body);
  return data.data;
}

export async function updateOrder(
  id: string,
  body: OrderUpdate,
): Promise<ProductionOrder> {
  const { data } = await api.patch<ApiResponse<ProductionOrder>>(
    `/orders/${id}`,
    body,
  );
  return data.data;
}

export async function deleteOrder(id: string): Promise<void> {
  await api.delete(`/orders/${id}`);
}

export async function releaseOrder(
  id: string,
  notes?: string,
): Promise<ProductionOrder> {
  const { data } = await api.post<ApiResponse<ProductionOrder>>(
    `/orders/${id}/release`,
    { notes },
  );
  return data.data;
}

export async function completeOrder(
  id: string,
  notes?: string,
): Promise<ProductionOrder> {
  const { data } = await api.post<ApiResponse<ProductionOrder>>(
    `/orders/${id}/complete`,
    { notes },
  );
  return data.data;
}

export async function closeOrder(
  id: string,
  notes?: string,
): Promise<ProductionOrder> {
  const { data } = await api.post<ApiResponse<ProductionOrder>>(
    `/orders/${id}/close`,
    { notes },
  );
  return data.data;
}
