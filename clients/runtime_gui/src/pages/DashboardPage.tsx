import { useQuery } from "@tanstack/react-query";
import { fetchOrderProgress, fetchShiftSummary } from "../api/runtime";
import type { MESEvent } from "../types";

interface Props {
  events: MESEvent[];
}

export default function DashboardPage({ events }: Props) {
  const { data: orders, isLoading } = useQuery({
    queryKey: ["order-progress"],
    queryFn: () => fetchOrderProgress(),
    refetchInterval: 10_000,
  });

  const { data: shift } = useQuery({
    queryKey: ["shift-summary"],
    queryFn: () => fetchShiftSummary(8),
    refetchInterval: 30_000,
  });

  const recentEvents = events.slice(-20).reverse();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Shop Floor Dashboard</h2>

      {/* Shift Summary */}
      {shift && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-lg font-semibold mb-3 text-gray-700">Shift Summary (Last 8 Hours)</h3>
          <pre className="text-sm text-gray-600 overflow-auto">{JSON.stringify(shift, null, 2)}</pre>
        </div>
      )}

      {/* Order Progress */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-lg font-semibold mb-3 text-gray-700">Active Order Progress</h3>
        {isLoading ? (
          <p className="text-gray-400">Loading…</p>
        ) : !orders || (orders as unknown[]).length === 0 ? (
          <p className="text-gray-400">No active orders</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 px-3">Order #</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Ordered</th>
                  <th className="py-2 px-3">Completed</th>
                  <th className="py-2 px-3">Scrapped</th>
                  <th className="py-2 px-3">Progress</th>
                </tr>
              </thead>
              <tbody>
                {(orders as Record<string, unknown>[]).map((o, i) => {
                  const ordered = Number(o.quantity_ordered ?? 0);
                  const completed = Number(o.quantity_completed ?? 0);
                  const pct = ordered > 0 ? Math.round((completed / ordered) * 100) : 0;
                  return (
                    <tr key={i} className="border-b hover:bg-gray-50">
                      <td className="py-2 px-3 font-mono">{String(o.order_number ?? "")}</td>
                      <td className="py-2 px-3">
                        <StatusBadge status={String(o.status ?? "")} />
                      </td>
                      <td className="py-2 px-3">{ordered}</td>
                      <td className="py-2 px-3">{completed}</td>
                      <td className="py-2 px-3">{Number(o.quantity_scrapped ?? 0)}</td>
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="h-2 rounded-full bg-indigo-600"
                              style={{ width: `${Math.min(pct, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">{pct}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Events */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-lg font-semibold mb-3 text-gray-700">Recent Events</h3>
        {recentEvents.length === 0 ? (
          <p className="text-gray-400">No events yet — waiting for WebSocket…</p>
        ) : (
          <div className="max-h-64 overflow-y-auto space-y-1">
            {recentEvents.map((e) => (
              <div key={e.event_id} className="flex gap-3 text-xs font-mono border-b py-1">
                <span className="text-gray-400 w-20 shrink-0">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-indigo-600 w-48 shrink-0">{e.event_type}</span>
                <span className="text-gray-500 truncate">{JSON.stringify(e.payload)}</span>
              </div>
            ))}
          </div>
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
