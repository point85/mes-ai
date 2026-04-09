import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowPathIcon, PlusIcon } from "@heroicons/react/24/outline";
import { fetchOrders, createLot } from "../api/runtime";
import type { ProductionOrder } from "../types";

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
                <th className="py-2 px-3">Order #</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Priority</th>
                <th className="py-2 px-3">Ordered</th>
                <th className="py-2 px-3">Completed</th>
                <th className="py-2 px-3">Scrapped</th>
                <th className="py-2 px-3">ERP Ref</th>
                <th className="py-2 px-3">Created</th>
                <th className="py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const canCreate = o.status === "released" || o.status === "in_progress";
                return (
                  <>
                    <tr key={o.id} className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => canCreate && toggleExpand(o.id)}>
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
                      <td className="py-2 px-3">
                        {canCreate && (
                          <button
                            onClick={(e) => { e.stopPropagation(); toggleExpand(o.id); }}
                            className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
                          >
                            <PlusIcon className="h-3.5 w-3.5" /> Lot
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedOrderId === o.id && canCreate && (
                      <tr key={`${o.id}-form`} className="bg-indigo-50">
                        <td colSpan={9} className="px-3 py-3">
                          <CreateLotForm order={o} onCreated={refresh} />
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function CreateLotForm({ order, onCreated }: { order: ProductionOrder; onCreated: () => void }) {
  const [quantity, setQuantity] = useState<string>(String(order.quantity_ordered - order.quantity_completed - order.quantity_scrapped));
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
    <div className="space-y-2">
      <p className="text-sm font-medium text-gray-700">Create Lot for {order.order_number}</p>
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Quantity</label>
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="input-field w-28"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Lot # (optional)</label>
          <input
            type="text"
            value={lotNumber}
            onChange={(e) => setLotNumber(e.target.value)}
            placeholder="Auto-generate"
            className="input-field w-48"
          />
        </div>
        <button
          onClick={handleCreate}
          disabled={loading || !quantity || parseInt(quantity) <= 0}
          className="btn-primary text-sm"
        >
          {loading ? "Creating…" : "Create Lot"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {success && <p className="text-xs text-green-600">{success}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    created: "bg-gray-100 text-gray-700",
    released: "bg-blue-100 text-blue-700",
    in_progress: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    closed: "bg-gray-200 text-gray-500",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status.replace("_", " ")}
    </span>
  );
}
