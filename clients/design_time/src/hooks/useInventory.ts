/**
 * TanStack Query hooks for Inventory Management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchStorageLocations,
  createStorageLocation,
  updateStorageLocation,
  deleteStorageLocation,
  fetchInventoryBalances,
  fetchInventoryTransactions,
} from "../api/inventory";
import type { StorageLocationCreate, StorageLocationUpdate } from "../types";

const KEYS = {
  locations: ["storageLocations"] as const,
  locationList: (type?: string, siteId?: string) =>
    ["storageLocations", "list", type, siteId] as const,
  balances: ["inventoryBalances"] as const,
  balanceList: (lotId?: string, locId?: string) =>
    ["inventoryBalances", "list", lotId, locId] as const,
  transactions: ["inventoryTransactions"] as const,
  transactionList: (lotId?: string, locId?: string, txnType?: string) =>
    ["inventoryTransactions", "list", lotId, locId, txnType] as const,
};

export function useStorageLocations(locationType?: string, siteId?: string) {
  return useQuery({
    queryKey: KEYS.locationList(locationType, siteId),
    queryFn: () => fetchStorageLocations(locationType, siteId),
  });
}

export function useCreateStorageLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StorageLocationCreate) => createStorageLocation(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.locations }),
  });
}

export function useUpdateStorageLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: StorageLocationUpdate & { id: string }) =>
      updateStorageLocation(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.locations }),
  });
}

export function useDeleteStorageLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteStorageLocation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.locations }),
  });
}

// ─── Inventory Balances ───────────────────────────────────────────────

export function useInventoryBalances(materialLotId?: string, locationId?: string) {
  return useQuery({
    queryKey: KEYS.balanceList(materialLotId, locationId),
    queryFn: () => fetchInventoryBalances(materialLotId, locationId),
  });
}

// ─── Inventory Transactions ───────────────────────────────────────────

export function useInventoryTransactions(
  materialLotId?: string,
  locationId?: string,
  transactionType?: string,
) {
  return useQuery({
    queryKey: KEYS.transactionList(materialLotId, locationId, transactionType),
    queryFn: () => fetchInventoryTransactions(materialLotId, locationId, transactionType),
  });
}
