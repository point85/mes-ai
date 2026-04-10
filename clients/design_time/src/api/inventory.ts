/**
 * Inventory Management API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  StorageLocation,
  StorageLocationCreate,
  StorageLocationUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Storage Locations ────────────────────────────────────────────────

export async function fetchStorageLocations(
  locationType?: string,
  siteId?: string,
): Promise<ApiListResponse<StorageLocation>> {
  const params: Record<string, string> = { limit: "200" };
  if (locationType) params.location_type = locationType;
  if (siteId) params.site_id = siteId;
  const { data } = await api.get<ApiListResponse<StorageLocation>>(
    "/storage-locations",
    { params },
  );
  return data;
}

export async function fetchStorageLocation(
  id: string,
): Promise<StorageLocation> {
  const { data } = await api.get<ApiResponse<StorageLocation>>(
    `/storage-locations/${id}`,
  );
  return data.data;
}

export async function createStorageLocation(
  body: StorageLocationCreate,
): Promise<StorageLocation> {
  const { data } = await api.post<ApiResponse<StorageLocation>>(
    "/storage-locations",
    body,
  );
  return data.data;
}

export async function updateStorageLocation(
  id: string,
  body: StorageLocationUpdate,
): Promise<StorageLocation> {
  const { data } = await api.patch<ApiResponse<StorageLocation>>(
    `/storage-locations/${id}`,
    body,
  );
  return data.data;
}

export async function deleteStorageLocation(id: string): Promise<void> {
  await api.delete(`/storage-locations/${id}`);
}
