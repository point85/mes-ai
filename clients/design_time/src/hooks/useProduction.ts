/**
 * TanStack Query hooks for Production Orders.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchOrders,
  createOrder,
  updateOrder,
  deleteOrder,
  releaseOrder,
  completeOrder,
  closeOrder,
} from "../api/production";
import type { OrderCreate, OrderUpdate } from "../types";

const KEYS = {
  all: ["orders"] as const,
  list: (status?: string, productId?: string) =>
    ["orders", "list", status, productId] as const,
};

export function useOrders(status?: string, productId?: string) {
  return useQuery({
    queryKey: KEYS.list(status, productId),
    queryFn: () => fetchOrders(status, productId),
  });
}

export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: OrderCreate) => createOrder(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: OrderUpdate & { id: string }) =>
      updateOrder(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteOrder(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useReleaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      releaseOrder(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useCompleteOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      completeOrder(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useCloseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      closeOrder(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}
