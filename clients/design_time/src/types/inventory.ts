/**
 * Inventory Management: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Storage Location ─────────────────────────────────────────────────

export const LOCATION_TYPES = [
  "receiving",
  "storage",
  "rip",
  "staging",
  "shipping",
] as const;

export type LocationType = (typeof LOCATION_TYPES)[number];

export interface StorageLocation {
  id: string;
  name: string;
  code: string;
  description: string | null;
  location_type: LocationType;
  aisle: string | null;
  bay: string | null;
  tier: string | null;
  site_id: string | null;
  capacity: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StorageLocationCreate {
  name: string;
  code: string;
  description?: string | null;
  location_type?: string;
  aisle?: string | null;
  bay?: string | null;
  tier?: string | null;
  site_id?: string | null;
  capacity?: number | null;
}

export interface StorageLocationUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  location_type?: string;
  aisle?: string | null;
  bay?: string | null;
  tier?: string | null;
  site_id?: string | null;
  capacity?: number | null;
}
