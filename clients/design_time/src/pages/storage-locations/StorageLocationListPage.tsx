/**
 * Storage Location List Page — table of storage locations with CRUD.
 *
 * Displays locations in a filterable table. Users can create, edit,
 * or soft-delete locations. Colour-coded badges for location type.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import {
  useStorageLocations,
  useDeleteStorageLocation,
} from "../../hooks/useInventory";
import { useSites } from "../../hooks/usePhysicalModel";
import type { StorageLocation, LocationType } from "../../types";
import { LOCATION_TYPES } from "../../types/inventory";
import LocationFormDialog from "./LocationFormDialog";

/* ── type badge colours ───────────────────────────────────────────── */
const TYPE_COLORS: Record<LocationType, string> = {
  receiving: "bg-blue-100 text-blue-800",
  storage: "bg-green-100 text-green-800",
  rip: "bg-amber-100 text-amber-800",
  staging: "bg-purple-100 text-purple-800",
  shipping: "bg-cyan-100 text-cyan-800",
};

const TYPE_LABELS: Record<LocationType, string> = {
  receiving: "Receiving",
  storage: "Storage",
  rip: "Raw-in-Process",
  staging: "Staging",
  shipping: "Shipping",
};

export default function StorageLocationListPage() {
  const [editingLoc, setEditingLoc] = useState<StorageLocation | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");

  const { data, isLoading, error } = useStorageLocations();
  const { data: sitesData } = useSites();
  const deleteMut = useDeleteStorageLocation();

  const locations = data?.data ?? [];
  const sites = sitesData?.data ?? [];

  const siteMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const s of sites) m.set(s.id, s.name);
    return m;
  }, [sites]);

  const filtered = useMemo(() => {
    let result = locations;
    if (typeFilter) {
      result = result.filter((loc) => loc.location_type === typeFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (loc) =>
          loc.name.toLowerCase().includes(q) ||
          loc.code.toLowerCase().includes(q) ||
          (loc.description ?? "").toLowerCase().includes(q),
      );
    }
    return result;
  }, [locations, typeFilter, search]);

  const handleDelete = (loc: StorageLocation) => {
    if (!confirm(`Delete location "${loc.code}" — ${loc.name}?`)) return;
    deleteMut.mutate(loc.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Storage Locations
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage warehouse and plant storage locations for inventory
            management.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Location
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search by name, code, or description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-72"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All Types</option>
          {LOCATION_TYPES.map((t) => (
            <option key={t} value={t}>
              {TYPE_LABELS[t]}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} location{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading locations…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load storage locations. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Position
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Site
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Capacity
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Active
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((loc) => {
                const positionParts = [loc.aisle, loc.bay, loc.tier].filter(
                  Boolean,
                );
                return (
                  <tr
                    key={loc.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                      {loc.code}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {loc.name}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[loc.location_type] ?? "bg-gray-100 text-gray-600"}`}
                      >
                        {TYPE_LABELS[loc.location_type] ?? loc.location_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {positionParts.length > 0
                        ? positionParts.join(" / ")
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {loc.site_id ? (siteMap.get(loc.site_id) ?? loc.site_id) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {loc.capacity != null ? loc.capacity : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {loc.is_active ? (
                        <span className="text-xs text-green-600 font-medium">
                          ✓
                        </span>
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setEditingLoc(loc)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                          title="Edit"
                        >
                          <PencilSquareIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(loc)}
                          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                          title="Delete"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No storage locations found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editingLoc) && (
        <LocationFormDialog
          location={editingLoc}
          onClose={() => {
            setShowCreate(false);
            setEditingLoc(null);
          }}
        />
      )}
    </div>
  );
}
