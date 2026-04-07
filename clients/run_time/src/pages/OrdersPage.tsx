import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchOrders } from "../api/runtime";

export default function OrdersPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders", statusFilter],
    queryFn: () => fetchOrders({ status: statusFilter || undefined }),
    refetchInterval: 10_000,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Production Orders</h2>

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
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const pct = o.quantity_ordered > 0
                  ? Math.round((o.quantity_completed / o.quantity_ordered) * 100)
                  : 0;
                return (
                  <tr key={o.id} className="border-b hover:bg-gray-50">
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
                );
              })}
            </tbody>
          </table>
        )}
      </div>
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
