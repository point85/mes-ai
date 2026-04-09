import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowPathIcon, ChevronDownIcon, ChevronRightIcon, PlusIcon } from "@heroicons/react/24/outline";
import { fetchOrders, fetchUnits, fetchLots, createLot, createUnit } from "../api/runtime";
import type { ProductionOrder, Unit, Lot } from "../types";

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [expandedOrderId, setExpandedOrderId] = useState<string | null>(null);

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders", statusFilter],
    queryFn: () => fetchOrders({ status: statusFilter || undefined }),
    refetchInterval: 10_000,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["orders"] });
    queryClient.invalidateQueries({ queryKey: ["lots"] });
    queryClient.invalidateQueries({ queryKey: ["units"] });
    queryClient.invalidateQueries({ queryKey: ["order-wip"] });
  };

  const toggleExpand = (id: string) =>
    setExpandedOrderId((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Production Orders</h2>
        <button onClick={refresh} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
          <ArrowPathIcon className="h-4 w-4" /> Refresh
        </button>
      </div>

      <div className="flex gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field">
            <option value="">All</option>
            <option value="created">Created</option>
            <option value="released">Released</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        {isLoading ? (
          <p className="p-5 text-gray-400">Loading…</p>
        ) : !orders || orders.length === 0 ? (
          <p className="p-5 text-gray-400">No orders found</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 px-3 w-6"></th>
                <th className="py-2 px-3">Order #</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Priority</th>
                <th className="py-2 px-3">Ordered</th>
                <th className="py-2 px-3">Completed</th>
                <th className="py-2 px-3">Scrapped</th>
                <th className="py-2 px-3">ERP Ref</th>
                <th className="py-2 px-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const expanded = expandedOrderId === o.id;
                return (
                  <OrderRow key={o.id} order={o} expanded={expanded} onToggle={() => toggleExpand(o.id)} onRefresh={refresh} />
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function OrderRow({ order: o, expanded, onToggle, onRefresh }: {
  order: ProductionOrder; expanded: boolean; onToggle: () => void; onRefresh: () => void;
}) {
  return (
    <>
      <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="py-2 px-3">
          {expanded
            ? <ChevronDownIcon className="h-4 w-4 text-gray-400" />
            : <ChevronRightIcon className="h-4 w-4 text-gray-400" />}
        </td>
        <td className="py-2 px-3 font-mono">{o.order_number}</td>
        <td className="py-2 px-3"><StatusBadge status={o.status} /></td>
        <td className="py-2 px-3">{o.priority}</td>
        <td className="py-2 px-3">{o.quantity_ordered}</td>
        <td className="py-2 px-3">{o.quantity_completed}</td>
        <td className="py-2 px-3">{o.quantity_scrapped}</td>
        <td className="py-2 px-3 text-xs text-gray-400">{o.erp_reference ?? "—"}</td>
        <td className="py-2 px-3 text-xs text-gray-400">
          {new Date(o.created_at).toLocaleString()}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50">
          <td colSpan={9} className="px-3 py-3">
            <OrderDetail order={o} onRefresh={onRefresh} />
          </td>
        </tr>
      )}
    </>
  );
}

function OrderDetail({ order, onRefresh }: { order: ProductionOrder; onRefresh: () => void }) {
  const [showCreateLot, setShowCreateLot] = useState(false);
  const [showCreateUnit, setShowCreateUnit] = useState(false);
  const canCreate = order.status === "released" || order.status === "in_progress";

  const { data: units = [] } = useQuery<Unit[]>({
    queryKey: ["order-wip", "units", order.id],
    queryFn: () => fetchUnits({ order_id: order.id }),
  });

  const { data: lots = [] } = useQuery<Lot[]>({
    queryKey: ["order-wip", "lots", order.id],
    queryFn: () => fetchLots({ order_id: order.id }),
  });

  return (
    <div className="space-y-3">
      {/* Create buttons */}
      {canCreate && (
        <div className="flex gap-2">
          <button
            onClick={() => { setShowCreateLot(!showCreateLot); setShowCreateUnit(false); }}
            className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded-md px-2 py-1"
          >
            <PlusIcon className="h-3.5 w-3.5" /> Create Lot
          </button>
          <button
            onClick={() => { setShowCreateUnit(!showCreateUnit); setShowCreateLot(false); }}
            className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded-md px-2 py-1"
          >
            <PlusIcon className="h-3.5 w-3.5" /> Create Unit
          </button>
        </div>
      )}

      {showCreateLot && <CreateLotForm order={order} onCreated={onRefresh} />}
      {showCreateUnit && <CreateUnitForm order={order} onCreated={onRefresh} />}

      {/* Lots */}
      {lots.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Lots ({lots.length})</h5>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400 border-b">
                <th className="py-1 px-2">Lot #</th>
                <th className="py-1 px-2">Qty</th>
                <th className="py-1 px-2">Status</th>
                <th className="py-1 px-2">Step</th>
              </tr>
            </thead>
            <tbody>
              {lots.map((l) => (
                <tr key={l.id} className="border-b">
                  <td className="py-1 px-2 font-mono">{l.lot_number}</td>
                  <td className="py-1 px-2">{l.quantity}</td>
                  <td className="py-1 px-2"><WipBadge status={l.status} /></td>
                  <td className="py-1 px-2 text-gray-500">{l.current_step_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Units */}
      {units.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Units ({units.length})</h5>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400 border-b">
                <th className="py-1 px-2">Serial #</th>
                <th className="py-1 px-2">Status</th>
                <th className="py-1 px-2">Step</th>
              </tr>
            </thead>
            <tbody>
              {units.map((u) => (
                <tr key={u.id} className="border-b">
                  <td className="py-1 px-2 font-mono">{u.serial_number}</td>
                  <td className="py-1 px-2"><WipBadge status={u.status} /></td>
                  <td className="py-1 px-2 text-gray-500">{u.current_step_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {lots.length === 0 && units.length === 0 && !showCreateLot && !showCreateUnit && (
        <p className="text-xs text-gray-400">No lots or units for this order</p>
      )}
    </div>
  );
}

function CreateLotForm({ order, onCreated }: { order: ProductionOrder; onCreated: () => void }) {
  const remaining = order.quantity_ordered - order.quantity_completed - order.quantity_scrapped;
  const [quantity, setQuantity] = useState<string>(String(remaining > 0 ? remaining : 1));
  const [lotNumber, setLotNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const lot = await createLot({
        order_id: order.id,
        product_id: order.product_id,
        quantity: parseInt(quantity),
        ...(lotNumber ? { lot_number: lotNumber } : {}),
      });
      setSuccess(`Lot ${lot.lot_number} created`);
      setLotNumber("");
      onCreated();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Failed to create lot";
      setError(m);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-indigo-50 rounded-md p-3 space-y-2">
      <p className="text-sm font-medium text-gray-700">Create Lot</p>
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Quantity</label>
          <input type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="input-field w-28" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Lot # (optional)</label>
          <input type="text" value={lotNumber} onChange={(e) => setLotNumber(e.target.value)} placeholder="Auto-generate" className="input-field w-48" />
        </div>
        <button onClick={handleCreate} disabled={loading || !quantity || parseInt(quantity) <= 0} className="btn-primary text-sm">
          {loading ? "Creating…" : "Create Lot"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {success && <p className="text-xs text-green-600">{success}</p>}
    </div>
  );
}

function CreateUnitForm({ order, onCreated }: { order: ProductionOrder; onCreated: () => void }) {
  const [serialNumber, setSerialNumber] = useState("");
  const [count, setCount] = useState("1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const n = parseInt(count) || 1;
      const created: string[] = [];
      for (let i = 0; i < n; i++) {
        const unit = await createUnit({
          order_id: order.id,
          product_id: order.product_id,
          ...(n === 1 && serialNumber ? { serial_number: serialNumber } : {}),
        });
        created.push(unit.serial_number);
      }
      setSuccess(`Created ${created.length} unit(s): ${created.join(", ")}`);
      setSerialNumber("");
      onCreated();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Failed to create unit";
      setError(m);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-indigo-50 rounded-md p-3 space-y-2">
      <p className="text-sm font-medium text-gray-700">Create Unit(s)</p>
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">How many</label>
          <input type="number" min="1" max="100" value={count} onChange={(e) => setCount(e.target.value)} className="input-field w-20" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Serial # (single unit only)</label>
          <input
            type="text"
            value={serialNumber}
            onChange={(e) => setSerialNumber(e.target.value)}
            placeholder="Auto-generate"
            className="input-field w-48"
            disabled={parseInt(count) > 1}
          />
        </div>
        <button onClick={handleCreate} disabled={loading || !count || parseInt(count) <= 0} className="btn-primary text-sm">
          {loading ? "Creating…" : "Create Unit(s)"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {success && <p className="text-xs text-green-600">{success}</p>}
    </div>
  );
}

function WipBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-blue-100 text-blue-700",
    in_process: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    scrapped: "bg-red-100 text-red-700",
    on_hold: "bg-orange-100 text-orange-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status.replace("_", " ")}
    </span>
  );
}
