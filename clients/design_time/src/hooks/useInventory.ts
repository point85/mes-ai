/**
 * TanStack Query hooks for Inventory Management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchStorageLocations,
  createStorageLocation,
  updateStorageLocation,
  deleteStorageLocation,
} from "../api/inventory";
import type { StorageLocationCreate, StorageLocationUpdate } from "../types";

const KEYS = {
  locations: ["storageLocations"] as const,
  locationList: (type?: string, siteId?: string) =>
    ["storageLocations", "list", type, siteId] as const,
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
