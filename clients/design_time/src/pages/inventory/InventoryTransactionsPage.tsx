/**
 * Inventory Transactions Page — read-only audit log of all inventory movements.
 *
 * Supports filtering by transaction type, location, and search by lot number.
 * Colour-coded badges for transaction types.
 */

import { useState, useMemo } from "react";
import { useInventoryTransactions } from "../../hooks/useInventory";
import { useStorageLocations } from "../../hooks/useInventory";
import { useMaterialLots } from "../../hooks/useMaterial";
import type { InventoryTransaction, TransactionType } from "../../types";
import { TRANSACTION_TYPES } from "../../types/inventory";

/* ── type badge colours ─────────────────────────────────────────── */
const TXN_COLORS: Record<TransactionType, string> = {
  receive: "bg-blue-100 text-blue-800",
  putaway: "bg-green-100 text-green-800",
  pick: "bg-amber-100 text-amber-800",
  move: "bg-purple-100 text-purple-800",
  consume: "bg-red-100 text-red-800",
  adjust: "bg-gray-100 text-gray-800",
};

const TXN_LABELS: Record<TransactionType, string> = {
  receive: "Receive",
  putaway: "Put Away",
  pick: "Pick",
  move: "Move",
  consume: "Consume",
  adjust: "Adjust",
};

export default function InventoryTransactionsPage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");

  const { data: txnData, isLoading, error } = useInventoryTransactions(
    undefined,
    locationFilter || undefined,
    typeFilter || undefined,
  );
  const { data: locData } = useStorageLocations();
  const { data: lotData } = useMaterialLots();

  const transactions: InventoryTransaction[] = txnData?.data ?? [];
  const locations = locData?.data ?? [];
  const lots = lotData?.data ?? [];

  const locationMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const l of locations) m.set(l.id, l.code);
    return m;
  }, [locations]);

  const lotMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const lot of lots) m.set(lot.id, lot.lot_number);
    return m;
  }, [lots]);

  const filtered = useMemo(() => {
    if (!search) return transactions;
    const q = search.toLowerCase();
    return transactions.filter((t) => {
      const lotNum = lotMap.get(t.material_lot_id) ?? t.material_lot_id;
      const reason = t.reason ?? "";
      return (
        lotNum.toLowerCase().includes(q) || reason.toLowerCase().includes(q)
      );
    });
  }, [transactions, search, lotMap]);

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "medium",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Inventory Transactions
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Audit trail of all inventory movements — receives, putaways, picks,
          moves, consumes, and adjustments.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search by lot number or reason…"
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
          {TRANSACTION_TYPES.map((t) => (
            <option key={t} value={t}>
              {TXN_LABELS[t]}
            </option>
          ))}
        </select>
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
          {filtered.length} transaction{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading transactions…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load inventory transactions. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Material Lot
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  From
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  To
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Qty
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Reason
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Reference
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-xs text-gray-500 whitespace-nowrap">
                    {formatTimestamp(t.performed_at)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${TXN_COLORS[t.transaction_type] ?? "bg-gray-100 text-gray-600"}`}
                    >
                      {TXN_LABELS[t.transaction_type] ?? t.transaction_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                    {lotMap.get(t.material_lot_id) ?? t.material_lot_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {t.from_location_id
                      ? (locationMap.get(t.from_location_id) ?? t.from_location_id.slice(0, 8))
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {t.to_location_id
                      ? (locationMap.get(t.to_location_id) ?? t.to_location_id.slice(0, 8))
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-medium text-gray-900">
                    {t.quantity.toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500 max-w-48 truncate" title={t.reason ?? undefined}>
                    {t.reason ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-gray-400">
                    {t.reference_type
                      ? `${t.reference_type}: ${t.reference_id?.slice(0, 8) ?? "?"}`
                      : "—"}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No inventory transactions found.
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
