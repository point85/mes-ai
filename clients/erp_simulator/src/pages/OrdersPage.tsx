import { useState } from "react";
import {
  readProductionOrders,
  deleteProductionOrder,
  type DBProductionOrder,
} from "../api/erp";

export default function OrdersPage() {
  const [data, setData] = useState<DBProductionOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRead = async () => {
    setLoading(true);
    setError(null);
    try {
      const orders = await readProductionOrders();
      setData(orders);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Read failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    setError(null);
    try {
      await deleteProductionOrder(id);
      setData((prev) => prev.filter((o) => o.id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  const fmtDate = (v: string | null) =>
    v ? new Date(v).toLocaleDateString() : "—";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={handleRead}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Reading…" : "Read Production Orders"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} orders</span>
        )}
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
          {error}
        </div>
      )}
      {data.length === 0 ? (
        <div className="text-center py-8 text-gray-500 bg-white rounded-lg border">
          Click &lsquo;Read Production Orders&rsquo; to load data from the database
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Order #", "ERP Ref", "Status", "Qty Ordered", "Qty Done", "Qty Scrap",
                  "Priority", "Planned Start", "Planned End", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.map((row) => {
                const busy = deleting === row.id;
                return (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap">{row.order_number}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.erp_reference ?? "—"}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.status}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.quantity_ordered}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.quantity_completed}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.quantity_scrapped}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.priority}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{fmtDate(row.planned_start)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{fmtDate(row.planned_end)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <button
                        onClick={() => handleDelete(row.id)}
                        disabled={busy}
                        className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                      >
                        {busy ? "…" : "Delete"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
