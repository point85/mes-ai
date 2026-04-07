import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { fetchOrderProgress, fetchShiftSummary } from "../api/runtime";
import type { MESEvent } from "../types";

interface WipCounts {
  queued: number;
  in_process: number;
  on_hold: number;
  completed: number;
  scrapped: number;
}

interface Props {
  events: MESEvent[];
}

export default function DashboardPage({ events }: Props) {
  const queryClient = useQueryClient();

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

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["order-progress"] });
    queryClient.invalidateQueries({ queryKey: ["shift-summary"] });
  };

  const recentEvents = events.slice(-20).reverse();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Shop Floor Dashboard</h2>
        <button onClick={refresh} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
          <ArrowPathIcon className="h-4 w-4" /> Refresh
        </button>
      </div>

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
                  <th className="py-2 px-3">WIP</th>
                  <th className="py-2 px-3">Throughput</th>
                </tr>
              </thead>
              <tbody>
                {(orders as Record<string, unknown>[]).map((o, i) => {
                  const ordered = Number(o.quantity_ordered ?? 0);
                  const completed = Number(o.quantity_completed ?? 0);
                  const scrapped = Number(o.quantity_scrapped ?? 0);
                  const wip = o.wip_counts as WipCounts | undefined;
                  const throughput = completed + scrapped;
                  const pctCompleted = ordered > 0 ? Math.round((completed / ordered) * 100) : 0;
                  const pctScrapped = ordered > 0 ? Math.round((scrapped / ordered) * 100) : 0;
                  return (
                    <tr key={i} className="border-b hover:bg-gray-50">
                      <td className="py-2 px-3 font-mono">{String(o.order_number ?? "")}</td>
                      <td className="py-2 px-3">
                        <StatusBadge status={String(o.status ?? "")} />
                      </td>
                      <td className="py-2 px-3">{ordered}</td>
                      <td className="py-2 px-3">{completed}</td>
                      <td className="py-2 px-3">{scrapped}</td>
                      <td className="py-2 px-3">
                        {wip ? (
                          <div className="flex gap-2 text-xs">
                            {wip.queued > 0 && <span className="text-blue-600">{wip.queued} queued</span>}
                            {wip.in_process > 0 && <span className="text-yellow-600">{wip.in_process} active</span>}
                            {wip.on_hold > 0 && <span className="text-orange-600">{wip.on_hold} held</span>}
                          </div>
                        ) : "—"}
                      </td>
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-28 bg-gray-200 rounded-full h-2.5 flex overflow-hidden">
                            {pctCompleted > 0 && (
                              <div
                                className="h-2.5 bg-green-500"
                                style={{ width: `${Math.min(pctCompleted, 100)}%` }}
                              />
                            )}
                            {pctScrapped > 0 && (
                              <div
                                className="h-2.5 bg-red-400"
                                style={{ width: `${Math.min(pctScrapped, 100)}%` }}
                              />
                            )}
                          </div>
                          <span className="text-xs text-gray-500 whitespace-nowrap">
                            {throughput}/{ordered}
                          </span>
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
