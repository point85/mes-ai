import type { StorageLocation, MaterialLot, TrackingMethod, TransactionType } from "../types";

/**
 * Format a storage location for display
 */
export function formatLocationName(location: StorageLocation | undefined, id: string | null): string {
  if (!id) return "—";
  if (!location) return id.slice(0, 8);
  return `${location.code} (${location.location_type})`;
}

/**
 * Format a material lot for display
 */
export function formatLotLabel(lot: MaterialLot | undefined, id: string): string {
  if (!lot) return id.slice(0, 8);
  if (lot.tracking_method === "serial") {
    return `${lot.lot_number} [SN: ${lot.serial_number}]`;
  }
  return lot.lot_number;
}

/**
 * Get the badge color classes for a tracking method
 */
export function getTrackingBadgeClass(method: TrackingMethod | null | undefined): string {
  if (!method) return "text-gray-400";
  return method === "serial" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700";
}

/**
 * Get the badge color classes for a transaction type
 */
export function getTransactionTypeClass(type: TransactionType | string): string {
  const colors: Record<string, string> = {
    receive: "bg-green-100 text-green-700",
    putaway: "bg-blue-100 text-blue-700",
    pick: "bg-purple-100 text-purple-700",
    transfer: "bg-indigo-100 text-indigo-700",
    consume: "bg-red-100 text-red-700",
    adjust: "bg-gray-100 text-gray-700",
  };
  return colors[type] || "bg-gray-100 text-gray-700";
}

/**
 * Get the badge color classes for a location type
 */
export function getLocationTypeClass(type: string): string {
  const colors: Record<string, string> = {
    receiving: "bg-blue-100 text-blue-700",
    storage: "bg-green-100 text-green-700",
    rip: "bg-yellow-100 text-yellow-700",
    staging: "bg-purple-100 text-purple-700",
    shipping: "bg-red-100 text-red-700",
  };
  return colors[type] || "bg-gray-100 text-gray-700";
}

/**
 * Format a date for display
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return "—";
  try {
    return new Date(dateString).toLocaleDateString();
  } catch {
    return dateString;
  }
}

/**
 * Format a datetime for display
 */
export function formatDateTime(dateString: string | null): string {
  if (!dateString) return "—";
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return dateString;
  }
}

/**
 * Format a number with locale string
 */
export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return "—";
  return num.toLocaleString();
}

/**
 * Extract error message from an API error
 */
export function extractApiError(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const resp = (err as { response?: { data?: { message?: string; detail?: unknown } } }).response;
    if (resp?.data?.message) return resp.data.message;
    if (resp?.data?.detail) {
      return typeof resp.data.detail === "string" ? resp.data.detail : JSON.stringify(resp.data.detail);
    }
  }
  return err instanceof Error ? err.message : "Operation failed";
}

/**
 * Get default location IDs for an operation type
 */
export function getDefaultLocationIds(
  opType: string,
  locations: StorageLocation[]
): { from_location_id?: string; to_location_id?: string; location_id?: string } {
  const receiving = locations.find((l) => l.location_type === "receiving")?.id ?? "";
  const storage = locations.find((l) => l.location_type === "storage")?.id ?? "";
  const staging = locations.find((l) => l.location_type === "staging")?.id ?? "";

  switch (opType) {
    case "receive":
      return { to_location_id: receiving };
    case "putaway":
      return { from_location_id: receiving, to_location_id: storage };
    case "pick":
      return { from_location_id: storage, to_location_id: staging };
    case "transfer":
      return { from_location_id: storage, to_location_id: storage };
    case "consume":
      return { from_location_id: storage };
    case "adjust":
      return { location_id: storage };
    default:
      return {};
  }
}

/**
 * Filter locations by operation type
 */
export function filterLocationsForOperation(opType: string, locations: StorageLocation[]): StorageLocation[] {
  switch (opType) {
    case "receive":
      return locations.filter((l) => l.location_type === "receiving" || l.location_type === "storage");
    case "putaway":
      return locations.filter((l) => l.location_type === "storage");
    default:
      return locations;
  }
}