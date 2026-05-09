import { useState, useEffect, useCallback } from "react";
import { ArrowPathIcon, CheckCircleIcon, ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import {
  fetchInventoryTransactions,
  fetchInventoryBalances,
  fetchStorageLocations,
  fetchMaterialLots,
  receiveInventory,
  putawayInventory,
  pickInventory,
  moveInventory,
  consumeInventory,
  adjustInventory,
} from "../api/runtime";
import type { InventoryTransaction, InventoryBalance, StorageLocation, MaterialLot } from "../types";

// ── Constants ────────────────────────────────────────────────────

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

type PageTab = "operations" | "balances" | "log";
type OpType = "receive" | "putaway" | "pick" | "move" | "consume" | "adjust";

const OP_LABELS: { id: OpType; label: string; color: string }[] = [
  { id: "receive", label: "Receive", color: "bg-green-600 hover:bg-green-700" },
  { id: "putaway", label: "Put Away", color: "bg-blue-600 hover:bg-blue-700" },
  { id: "pick", label: "Pick", color: "bg-amber-600 hover:bg-amber-700" },
  { id: "move", label: "Move", color: "bg-purple-600 hover:bg-purple-700" },
  { id: "consume", label: "Consume", color: "bg-red-600 hover:bg-red-700" },
  { id: "adjust", label: "Adjust", color: "bg-gray-600 hover:bg-gray-700" },
];

// ── Helpers ──────────────────────────────────────────────────────

function extractError(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const resp = (err as { response?: { data?: { message?: string; detail?: unknown } } }).response;
    if (resp?.data?.message) return resp.data.message;
    if (resp?.data?.detail) {
      if (typeof resp.data.detail === "string") return resp.data.detail;
      return JSON.stringify(resp.data.detail);
    }
  }
  return err instanceof Error ? err.message : "Operation failed";
}

// ── Main Component ───────────────────────────────────────────────

export default function InventoryPage() {
  const [tab, setTab] = useState<PageTab>("operations");
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [locationMap, setLocationMap] = useState<Map<string, StorageLocation>>(new Map());
  const [lotMap, setLotMap] = useState<Map<string, MaterialLot>>(new Map());

  const loadRefData = useCallback(async () => {
    const [locs, mLots] = await Promise.all([fetchStorageLocations(), fetchMaterialLots()]);
    setLocations(locs);
    setLots(mLots);
    setLocationMap(new Map(locs.map((l) => [l.id, l])));
    setLotMap(new Map(mLots.map((l) => [l.id, l])));
  }, []);

  useEffect(() => { loadRefData(); }, [loadRefData]);

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
        <h2 className="text-2xl font-bold text-gray-800">Inventory</h2>
        <button
          onClick={loadRefData}
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
        >
          <ArrowPathIcon className="h-4 w-4" /> Refresh Data
        </button>
      </div>

      {/* Page tabs */}
      <div className="flex gap-1 border-b">
        {(["operations", "balances", "log"] as PageTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${
              tab === t
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "log" ? "Transaction Log" : t === "balances" ? "Balances" : "Operations"}
          </button>
        ))}
      </div>

      {tab === "operations" && (
        <OperationsPanel locations={locations} lots={lots} onSuccess={loadRefData} />
      )}
      {tab === "balances" && (
        <BalancesPanel locationMap={locationMap} lotMap={lotMap} />
      )}
      {tab === "log" && (
        <TransactionLog locationMap={locationMap} lotMap={lotMap} locName={locName} lotLabel={lotLabel} />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Operations Panel — tabbed forms for each action type
// ═══════════════════════════════════════════════════════════════════

function OperationsPanel({
  locations,
  lots,
  onSuccess,
}: {
  locations: StorageLocation[];
  lots: MaterialLot[];
  onSuccess: () => void;
}) {
  const [op, setOp] = useState<OpType>("receive");
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [lotId, setLotId] = useState("");
  const [fromLocId, setFromLocId] = useState("");
  const [toLocId, setToLocId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");

  const availableLots = lots.filter((l) => l.status === "available" || l.status === "reserved");

  const reset = () => {
    setLotId("");
    setFromLocId("");
    setToLocId("");
    setQuantity("");
    setReason("");
    setError(null);
  };

  const switchOp = (newOp: OpType) => {
    setOp(newOp);
    reset();
    setSuccess(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setError("Quantity must be a positive number");
      setSubmitting(false);
      return;
    }

    try {
      switch (op) {
        case "receive":
          await receiveInventory({
            material_lot_id: lotId,
            to_location_id: toLocId,
            quantity: qty,
            reason: reason || undefined,
          });
          break;
        case "putaway":
          await putawayInventory({
            material_lot_id: lotId,
            from_location_id: fromLocId,
            to_location_id: toLocId,
            quantity: qty,
            reason: reason || undefined,
          });
          break;
        case "pick":
          await pickInventory({
            material_lot_id: lotId,
            from_location_id: fromLocId,
            to_location_id: toLocId,
            quantity: qty,
            reason: reason || undefined,
          });
          break;
        case "move":
          await moveInventory({
            material_lot_id: lotId,
            from_location_id: fromLocId,
            to_location_id: toLocId,
            quantity: qty,
            reason: reason || undefined,
          });
          break;
        case "consume":
          await consumeInventory({
            material_lot_id: lotId,
            from_location_id: fromLocId,
            quantity: qty,
            reason: reason || undefined,
          });
          break;
        case "adjust":
          if (!reason.trim()) {
            setError("Reason is required for adjustments");
            setSubmitting(false);
            return;
          }
          await adjustInventory({
            material_lot_id: lotId,
            location_id: fromLocId,
            quantity: qty,
            reason: reason,
          });
          break;
      }
      const lotName = lots.find((l) => l.id === lotId)?.lot_number ?? lotId.slice(0, 8);
      setSuccess(`${op.charAt(0).toUpperCase() + op.slice(1)} of ${qty} for lot ${lotName} completed.`);
      reset();
      onSuccess();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  // Determine which fields to show per operation
  const needsFrom = op !== "receive";
  const needsTo = op !== "consume" && op !== "adjust";
  const fromLabel = op === "adjust" ? "Location" : "From Location";

  return (
    <div className="space-y-4">
      {/* Operation selector */}
      <div className="flex gap-2 flex-wrap">
        {OP_LABELS.map((o) => (
          <button
            key={o.id}
            onClick={() => switchOp(o.id)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              op === o.id
                ? `${o.color} text-white`
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Status messages */}
      {success && (
        <div className="flex items-center gap-2 bg-green-50 text-green-700 rounded-md p-3 text-sm">
          <CheckCircleIcon className="h-5 w-5" />
          {success}
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 text-red-700 rounded-md p-3 text-sm">
          <ExclamationTriangleIcon className="h-5 w-5" />
          {error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-5 space-y-4">
        <h3 className="text-lg font-semibold text-gray-700 capitalize">{op} Inventory</h3>

        {/* Material Lot */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Material Lot</label>
          <select
            value={lotId}
            onChange={(e) => setLotId(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">— Select lot —</option>
            {availableLots.map((l) => (
              <option key={l.id} value={l.id}>
                {l.lot_number} (on-hand: {l.quantity_on_hand})
              </option>
            ))}
          </select>
        </div>

        {/* From Location */}
        {needsFrom && (
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">{fromLabel}</label>
            <select
              value={fromLocId}
              onChange={(e) => setFromLocId(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">— Select location —</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code} — {l.name} ({l.location_type})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* To Location */}
        {needsTo && (
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">To Location</label>
            <select
              value={toLocId}
              onChange={(e) => setToLocId(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">— Select location —</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code} — {l.name} ({l.location_type})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Quantity */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            {op === "adjust" ? "New Quantity (absolute)" : "Quantity"}
          </label>
          <input
            type="number"
            step="any"
            min={op === "adjust" ? "0" : "0.001"}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
            placeholder={op === "adjust" ? "Set absolute quantity" : "Enter quantity"}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Reason */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Reason {op === "adjust" && <span className="text-red-500">*</span>}
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required={op === "adjust"}
            placeholder={op === "adjust" ? "Reason required for adjustments" : "Optional reason or note"}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className={`w-full py-2.5 rounded-md text-white text-sm font-medium transition-colors disabled:opacity-50 ${
            OP_LABELS.find((o) => o.id === op)?.color ?? "bg-indigo-600 hover:bg-indigo-700"
          }`}
        >
          {submitting ? "Processing…" : `Submit ${op.charAt(0).toUpperCase() + op.slice(1)}`}
        </button>
      </form>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Balances Panel — current stock at each location
// ═══════════════════════════════════════════════════════════════════

function BalancesPanel({
  locationMap,
  lotMap,
}: {
  locationMap: Map<string, StorageLocation>;
  lotMap: Map<string, MaterialLot>;
}) {
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setBalances(await fetchInventoryBalances());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load balances");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const locName = (id: string) => locationMap.get(id)?.code ?? id.slice(0, 8);
  const lotLabel = (id: string) => lotMap.get(id)?.lot_number ?? id.slice(0, 8);

  const locations = Array.from(locationMap.values()).sort((a, b) => a.code.localeCompare(b.code));

  const filtered = balances.filter((b) => {
    if (search && !lotLabel(b.material_lot_id).toLowerCase().includes(search.toLowerCase())) return false;
    if (locationFilter && b.location_id !== locationFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-700">Current Inventory Balances</h3>
        <button onClick={load} disabled={loading} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 disabled:opacity-50">
          <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search by lot number…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-56"
        />
        <select
          value={locationFilter}
          onChange={(e) => setLocationFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All Locations</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>{loc.code} — {loc.name}</option>
          ))}
        </select>
        <span className="text-xs text-gray-400">{filtered.length} balance{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Material Lot</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Location</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">On Hand</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Reserved</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Available</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {loading ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">Loading…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">{search || locationFilter ? "No matches found." : "No inventory balances found."}</td></tr>
              ) : (
                filtered.map((b) => {
                  const available = b.quantity_on_hand - b.quantity_reserved;
                  return (
                    <tr key={b.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">{lotLabel(b.material_lot_id)}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">{locName(b.location_id)}</td>
                      <td className="px-4 py-2 text-sm text-gray-900 text-right font-mono">{b.quantity_on_hand}</td>
                      <td className="px-4 py-2 text-sm text-gray-600 text-right font-mono">{b.quantity_reserved}</td>
                      <td className={`px-4 py-2 text-sm text-right font-mono font-semibold ${available > 0 ? "text-green-700" : "text-red-600"}`}>
                        {available}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Transaction Log — read-only audit trail (original view)
// ═══════════════════════════════════════════════════════════════════

function TransactionLog({
  locationMap,
  lotMap,
  locName,
  lotLabel,
}: {
  locationMap: Map<string, StorageLocation>;
  lotMap: Map<string, MaterialLot>;
  locName: (id: string | null) => string;
  lotLabel: (id: string) => string;
}) {
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setTransactions(await fetchInventoryTransactions(typeFilter ? { transaction_type: typeFilter } : undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [typeFilter]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-700">Transaction Log</h3>
        <button onClick={load} disabled={loading} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 disabled:opacity-50">
          <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
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

      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Time</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Material Lot</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">From</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">To</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Qty</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {loading && transactions.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">Loading…</td></tr>
              ) : transactions.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">No inventory transactions found.</td></tr>
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
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TYPE_COLORS[txn.transaction_type] ?? "bg-gray-100 text-gray-600"}`}>
                          {txn.transaction_type}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">{lotLabel(txn.material_lot_id)}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">{locName(txn.from_location_id)}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">{locName(txn.to_location_id)}</td>
                      <td className="px-4 py-2 text-sm text-gray-900 text-right font-mono">{txn.quantity}</td>
                      <td className="px-4 py-2 text-sm text-gray-500 max-w-[200px] truncate">{txn.reason ?? "—"}</td>
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
