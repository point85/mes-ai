import { useState, useEffect, useCallback, useMemo } from "react";
import { ArrowPathIcon, CheckCircleIcon, ExclamationTriangleIcon, XMarkIcon, PlusIcon, PencilSquareIcon } from "@heroicons/react/24/outline";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
  fetchInventoryTransactions,
  fetchInventoryBalances,
  fetchStorageLocations,
  fetchMaterialLots,
  createMaterialLot,
  updateMaterialLot,
  fetchMaterials,
  receiveInventory,
  putawayInventory,
  pickInventory,
  moveInventory,
  consumeInventory,
  adjustInventory,
} from "../api/runtime";
import type { InventoryTransaction, InventoryBalance, StorageLocation, MaterialLot, Material } from "../types";

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

type PageTab = "operations" | "balances" | "log" | "lots";
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
  const [materialMap, setMaterialMap] = useState<Map<string, Material>>(new Map());

  const loadRefData = useCallback(async () => {
    const [locs, mLots, mats] = await Promise.all([fetchStorageLocations(), fetchMaterialLots(), fetchMaterials()]);
    setLocations(locs);
    setLots(mLots);
    setLocationMap(new Map(locs.map((l) => [l.id, l])));
    setLotMap(new Map(mLots.map((l) => [l.id, l])));
    setMaterialMap(new Map(mats.map((m) => [m.id, m])));
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
      </div>

      {/* Page tabs */}
      <div className="flex gap-1 border-b">
        {(["operations", "balances", "lots", "log"] as PageTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "log" ? "Transaction Log" : t === "balances" ? "Balances" : t === "lots" ? "Material Lots" : "Operations"}
          </button>
        ))}
      </div>

      {tab === "operations" && (
        <OperationsPanel locations={locations} lots={lots} onSuccess={loadRefData} />
      )}
      {tab === "balances" && (
        <BalancesPanel locationMap={locationMap} lotMap={lotMap} materialMap={materialMap} />
      )}
      {tab === "log" && (
        <TransactionLog locationMap={locationMap} lotMap={lotMap} locName={locName} lotLabel={lotLabel} />
      )}
      {tab === "lots" && (
        <LotsPanel />
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
  materialMap,
}: {
  locationMap: Map<string, StorageLocation>;
  lotMap: Map<string, MaterialLot>;
  materialMap: Map<string, Material>;
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
  const getLot = (id: string) => lotMap.get(id);
  const getMaterial = (lotId: string) => {
    const lot = lotMap.get(lotId);
    return lot ? materialMap.get(lot.material_id) : undefined;
  };

  const locations = Array.from(locationMap.values()).sort((a, b) => a.code.localeCompare(b.code));

  const filtered = balances.filter((b) => {
    if (search) {
      const lot = getLot(b.material_lot_id);
      const mat = getMaterial(b.material_lot_id);
      const haystack = [
        lot?.lot_number ?? "",
        mat?.name ?? "",
        mat?.code ?? "",
        mat?.description ?? "",
      ].join(" ").toLowerCase();
      if (!haystack.includes(search.toLowerCase())) return false;
    }
    if (locationFilter && b.location_id !== locationFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-700">Current Inventory Balances</h3>
        <button onClick={load} disabled={loading} className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 shadow-sm">
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
        <button
          onClick={() => { setSearch(""); setLocationFilter(""); }}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 shadow-sm border border-gray-300"
        >
          <XMarkIcon className="h-4 w-4" /> Clear
        </button>
        <span className="text-xs text-gray-400">{filtered.length} balance{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Lot #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Material</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Location</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">On Hand</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Reserved</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Available</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {loading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">Loading…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">{search || locationFilter ? "No matches found." : "No inventory balances found."}</td></tr>
              ) : (
                filtered.map((b) => {
                  const available = b.quantity_on_hand - b.quantity_reserved;
                  const lot = getLot(b.material_lot_id);
                  const mat = getMaterial(b.material_lot_id);
                  return (
                    <tr key={b.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm font-mono font-medium text-gray-900">{lot?.lot_number ?? b.material_lot_id.slice(0, 8)}</td>
                      <td className="px-4 py-2 text-sm text-gray-700">
                        {mat ? (
                          <div>
                            <span className="font-medium">{mat.code}</span> — {mat.name}
                            {mat.description && <div className="text-xs text-gray-400 mt-0.5">{mat.description}</div>}
                          </div>
                        ) : "—"}
                      </td>
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
  const [lotSearch, setLotSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setTransactions(await fetchInventoryTransactions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const locations = Array.from(locationMap.values()).sort((a, b) => a.code.localeCompare(b.code));

  const filtered = transactions.filter((txn) => {
    if (lotSearch && !lotLabel(txn.material_lot_id).toLowerCase().includes(lotSearch.toLowerCase())) return false;
    if (typeFilter && txn.transaction_type !== typeFilter) return false;
    if (locationFilter && txn.from_location_id !== locationFilter && txn.to_location_id !== locationFilter) return false;
    return true;
  });

  const handleClear = () => {
    setLotSearch("");
    setTypeFilter("");
    setLocationFilter("");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-700">Transaction Log</h3>
        <button onClick={load} disabled={loading} className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 shadow-sm">
          <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search by lot number…"
          value={lotSearch}
          onChange={(e) => setLotSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-48"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          {TXN_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
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
        <button
          onClick={handleClear}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 shadow-sm border border-gray-300"
        >
          <XMarkIcon className="h-4 w-4" /> Clear
        </button>
        <span className="text-xs text-gray-400">{filtered.length} transaction{filtered.length !== 1 ? "s" : ""}</span>
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
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">{lotSearch || typeFilter || locationFilter ? "No matches found." : "No inventory transactions found."}</td></tr>
              ) : (
                filtered
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
    </div>
  );
}

// ── Material Lots Panel ──────────────────────────────────────────

const LOT_STATUSES = ["available", "reserved", "consumed", "expired"] as const;
type LotStatus = typeof LOT_STATUSES[number];

const STATUS_COLORS: Record<string, string> = {
  available: "bg-green-100 text-green-700",
  reserved: "bg-blue-100 text-blue-700",
  consumed: "bg-gray-100 text-gray-600",
  expired: "bg-red-100 text-red-700",
};

interface LotFormState {
  material_id: string;
  lot_number: string;
  quantity_on_hand: string;
  received_date: string;
  expiry_date: string;
  supplier: string;
  status: LotStatus;
}

const EMPTY_LOT_FORM: LotFormState = {
  material_id: "",
  lot_number: "",
  quantity_on_hand: "0",
  received_date: "",
  expiry_date: "",
  supplier: "",
  status: "available",
};

function toDateInput(iso: string | null | undefined): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

interface LotFormDialogProps {
  lot: MaterialLot | null;
  materials: Material[];
  onClose: () => void;
  onSaved: () => void;
}

function LotFormDialog({ lot, materials, onClose, onSaved }: LotFormDialogProps) {
  const isEdit = !!lot;
  const [form, setForm] = useState<LotFormState>(
    lot
      ? {
          material_id: lot.material_id,
          lot_number: lot.lot_number,
          quantity_on_hand: String(lot.quantity_on_hand),
          received_date: toDateInput(lot.received_date),
          expiry_date: toDateInput(lot.expiry_date),
          supplier: lot.supplier ?? "",
          status: (LOT_STATUSES as readonly string[]).includes(lot.status)
            ? (lot.status as LotStatus)
            : "available",
        }
      : { ...EMPTY_LOT_FORM }
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sortedMaterials = useMemo(
    () => [...materials].sort((a, b) => a.code.localeCompare(b.code)),
    [materials]
  );

  const set = (field: keyof LotFormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!form.material_id) { setError("Material is required"); return; }
    if (!form.lot_number.trim()) { setError("Lot number is required"); return; }
    if (form.lot_number.includes(" ")) { setError("Lot number must not contain spaces"); return; }
    const qty = parseFloat(form.quantity_on_hand);
    if (isNaN(qty) || qty < 0) { setError("Quantity must be ≥ 0"); return; }

    setSaving(true);
    try {
      const payload = {
        lot_number: form.lot_number.trim(),
        quantity_on_hand: qty,
        received_date: form.received_date || null,
        expiry_date: form.expiry_date || null,
        supplier: form.supplier.trim() || null,
      };
      if (isEdit) {
        await updateMaterialLot(lot!.id, { ...payload, status: form.status });
      } else {
        await createMaterialLot({ material_id: form.material_id, ...payload });
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail ?? "An error occurred. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Material Lot" : "New Material Lot"}
            </DialogTitle>
            <button onClick={onClose} className="rounded p-1 text-gray-400 hover:text-gray-600">
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Material</label>
              <select
                value={form.material_id}
                onChange={set("material_id")}
                disabled={isEdit}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100"
              >
                <option value="">— Select material —</option>
                {sortedMaterials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.code} — {m.name} ({m.material_type})
                  </option>
                ))}
              </select>
              {isEdit && (
                <p className="mt-1 text-xs text-gray-400">Material cannot be changed after creation.</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Lot Number</label>
                <input
                  value={form.lot_number}
                  onChange={set("lot_number")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="LOT-2026-0001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Quantity on Hand</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={form.quantity_on_hand}
                  onChange={set("quantity_on_hand")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Received Date <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="date"
                  value={form.received_date}
                  onChange={set("received_date")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Expiry Date <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="date"
                  value={form.expiry_date}
                  onChange={set("expiry_date")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Supplier <span className="text-gray-400">(optional)</span>
              </label>
              <input
                value={form.supplier}
                onChange={set("supplier")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="Acme Supplies, Inc."
              />
            </div>

            {isEdit && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <select
                  value={form.status}
                  onChange={set("status")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {LOT_STATUSES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-400">
                  New lots default to <code>available</code>. Use this to manually reserve, expire, or mark as consumed.
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
              >
                {saving ? "Saving…" : isEdit ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}

function LotsPanel() {
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materialFilter, setMaterialFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dialogLot, setDialogLot] = useState<MaterialLot | null | "new">(null);

  const matById = useMemo(() => {
    const map = new Map<string, Material>();
    materials.forEach((m) => map.set(m.id, m));
    return map;
  }, [materials]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [lotsData, matsData] = await Promise.all([
        fetchMaterialLots(materialFilter || undefined, statusFilter || undefined),
        fetchMaterials(),
      ]);
      setLots(lotsData);
      setMaterials(matsData);
    } catch {
      setError("Failed to load material lots.");
    } finally {
      setLoading(false);
    }
  }, [materialFilter, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={materialFilter}
          onChange={(e) => setMaterialFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All Materials</option>
          {[...materials].sort((a, b) => a.code.localeCompare(b.code)).map((m) => (
            <option key={m.id} value={m.id}>{m.code} — {m.name}</option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All Statuses</option>
          {LOT_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>

        <div className="ml-auto">
          <button
            onClick={() => setDialogLot("new")}
            className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
          >
            <PlusIcon className="h-4 w-4" />
            New Lot
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700">
          <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Lot #</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Material</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500 uppercase tracking-wide text-xs">On Hand</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500 uppercase tracking-wide text-xs">Reserved</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Received</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Expiry</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Supplier</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {loading && lots.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : lots.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                {materialFilter || statusFilter ? "No lots match the current filters." : "No material lots found. Create one to get started."}
              </td></tr>
            ) : (
              lots.map((lot) => {
                const mat = matById.get(lot.material_id);
                return (
                  <tr key={lot.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2 font-mono font-medium text-gray-900">{lot.lot_number}</td>
                    <td className="px-4 py-2 text-gray-700">
                      {mat ? <><span className="font-medium">{mat.code}</span> — {mat.name}</> : lot.material_id}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-gray-900">{lot.quantity_on_hand}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-600">{lot.quantity_reserved}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[lot.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {lot.status === "available" && <CheckCircleIcon className="mr-1 h-3 w-3" />}
                        {lot.status === "expired" && <ExclamationTriangleIcon className="mr-1 h-3 w-3" />}
                        {lot.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-600">{lot.received_date ? toDateInput(lot.received_date) : "—"}</td>
                    <td className="px-4 py-2 text-gray-600">{lot.expiry_date ? toDateInput(lot.expiry_date) : "—"}</td>
                    <td className="px-4 py-2 text-gray-600 max-w-[160px] truncate">{lot.supplier ?? "—"}</td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => setDialogLot(lot)}
                        className="flex items-center gap-1 rounded px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50"
                      >
                        <PencilSquareIcon className="h-3.5 w-3.5" />
                        Edit
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {dialogLot !== null && (
        <LotFormDialog
          lot={dialogLot === "new" ? null : dialogLot}
          materials={materials}
          onClose={() => setDialogLot(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
