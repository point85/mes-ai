import { useState, useEffect } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import {
  fetchInventoryTransactions,
  fetchStorageLocations,
  fetchMaterialLots,
} from "../api/runtime";
import type { InventoryTransaction, StorageLocation, MaterialLot } from "../types";

const TXN_TYPES = [
  { label: "All", value: "" },
  { label: "Receive", value: "receive" },
  { label: "Put Away", value: "putaway" },
  { label: "Pick", value: "pick" },
  { label: "Move", value: "move" },
  { label: "Consume", value: "consume" },
  { label: "Adjust", value: "adjust" },
];

const TYPE_COLORS: Record<string, string> = {
  receive: "bg-green-100 text-green-700",
  putaway: "bg-blue-100 text-blue-700",
  pick: "bg-amber-100 text-amber-700",
  move: "bg-purple-100 text-purple-700",
  consume: "bg-red-100 text-red-700",
  adjust: "bg-gray-100 text-gray-700",
};

export default function InventoryPage() {
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [locationMap, setLocationMap] = useState<Map<string, StorageLocation>>(new Map());
  const [lotMap, setLotMap] = useState<Map<string, MaterialLot>>(new Map());
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [txns, locations, lots] = await Promise.all([
        fetchInventoryTransactions(typeFilter ? { transaction_type: typeFilter } : undefined),
        fetchStorageLocations(),
        fetchMaterialLots(),
      ]);
      setTransactions(txns);
      setLocationMap(new Map(locations.map((l) => [l.id, l])));
      setLotMap(new Map(lots.map((l) => [l.id, l])));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load inventory data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [typeFilter]);

  const locName = (id: string | null) => {
    if (!id) return "—";
    const loc = locationMap.get(id);
    return loc ? loc.code : id.slice(0, 8);
  };

  const lotLabel = (id: string) => {
    const lot = lotMap.get(id);
    return lot ? lot.lot_number : id.slice(0, 8);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Inventory Transactions</h2>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 disabled:opacity-50"
        >
          <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Type filter */}
      <div className="flex gap-2 flex-wrap">
        {TXN_TYPES.map((t) => (
          <button
            key={t.value}
            onClick={() => setTypeFilter(t.value)}
            className={`px-3 py-1 text-sm rounded-full font-medium transition-colors ${
              typeFilter === t.value
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Transactions table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Time
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
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {loading && transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">
                    Loading…
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">
                    No inventory transactions found.
                  </td>
                </tr>
              ) : (
                transactions
                  .slice()
                  .sort((a, b) => new Date(b.performed_at).getTime() - new Date(a.performed_at).getTime())
                  .map((txn) => (
                    <tr key={txn.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2 text-sm text-gray-600 font-mono whitespace-nowrap">
                        {new Date(txn.performed_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            TYPE_COLORS[txn.transaction_type] ?? "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {txn.transaction_type}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">
                        {lotLabel(txn.material_lot_id)}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {locName(txn.from_location_id)}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {locName(txn.to_location_id)}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-900 text-right font-mono">
                        {txn.quantity}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500 max-w-[200px] truncate">
                        {txn.reason ?? "—"}
                      </td>
                    </tr>
                  ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        Showing {transactions.length} transaction{transactions.length !== 1 ? "s" : ""}
        {typeFilter && ` (filtered: ${typeFilter})`}
      </p>
    </div>
  );
}
