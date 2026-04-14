/**
 * Inventory Balances Page — read-only table showing current stock by lot+location.
 *
 * Resolves material_lot_id and location_id to human-readable names.
 * Supports filtering by location and search by lot number.
 */

import { useState, useMemo } from "react";
import { useInventoryBalances } from "../../hooks/useInventory";
import { useStorageLocations } from "../../hooks/useInventory";
import { useMaterialLots } from "../../hooks/useMaterial";
import type { InventoryBalance } from "../../types";

export default function InventoryBalancesPage() {
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");

  const { data: balData, isLoading, error } = useInventoryBalances(
    undefined,
    locationFilter || undefined,
  );
  const { data: locData } = useStorageLocations();
  const { data: lotData } = useMaterialLots();

  const balances: InventoryBalance[] = balData?.data ?? [];
  const locations = locData?.data ?? [];
  const lots = lotData?.data ?? [];

  const locationMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const l of locations) m.set(l.id, `${l.code} — ${l.name}`);
    return m;
  }, [locations]);

  const lotMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const lot of lots) m.set(lot.id, lot.lot_number);
    return m;
  }, [lots]);

  const filtered = useMemo(() => {
    if (!search) return balances;
    const q = search.toLowerCase();
    return balances.filter((b) => {
      const lotNum = lotMap.get(b.material_lot_id) ?? b.material_lot_id;
      const locName = locationMap.get(b.location_id) ?? b.location_id;
      return (
        lotNum.toLowerCase().includes(q) || locName.toLowerCase().includes(q)
      );
    });
  }, [balances, search, lotMap, locationMap]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Inventory Balances
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Current stock levels by material lot and storage location.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search by lot number or location…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-72"
        />
        <select
          value={locationFilter}
          onChange={(e) => setLocationFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All Locations</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.code} — {loc.name}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} balance{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading balances…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load inventory balances. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Material Lot
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Location
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  On Hand
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Reserved
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Available
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Active
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((b) => {
                const available = b.quantity_on_hand - b.quantity_reserved;
                return (
                  <tr
                    key={b.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                      {lotMap.get(b.material_lot_id) ?? b.material_lot_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {locationMap.get(b.location_id) ?? b.location_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-medium text-gray-900">
                      {b.quantity_on_hand.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right text-amber-600">
                      {b.quantity_reserved > 0 ? b.quantity_reserved.toLocaleString() : "—"}
                    </td>
                    <td className={`px-4 py-2.5 text-sm text-right font-medium ${available > 0 ? "text-green-700" : "text-red-600"}`}>
                      {available.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {b.is_active ? (
                        <span className="text-xs text-green-600 font-medium">✓</span>
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No inventory balances found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
