import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { fetchUnits, fetchLots, fetchUnitStepContext, fetchLotStepContext } from "../api/runtime";
import { useState } from "react";
import type { StepContext } from "../types";
import StepProcessingPanel from "../components/StepProcessingPanel";

export default function ActiveWipPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<"units" | "lots">("units");
  const [statusFilter, setStatusFilter] = useState<string>("in_process");
  const [context, setContext] = useState<StepContext | null>(null);

  const { data: units, isLoading: unitsLoading } = useQuery({
    queryKey: ["units", statusFilter],
    queryFn: () => fetchUnits({ status: statusFilter || undefined }),
    enabled: view === "units",
    refetchInterval: 10_000,
  });

  const { data: lots, isLoading: lotsLoading } = useQuery({
    queryKey: ["lots", statusFilter],
    queryFn: () => fetchLots({ status: statusFilter || undefined }),
    enabled: view === "lots",
    refetchInterval: 10_000,
  });

  const openContext = async (type: "unit" | "lot", id: string) => {
    try {
      if (type === "unit") {
        setContext(await fetchUnitStepContext(id));
      } else {
        setContext(await fetchLotStepContext(id));
      }
    } catch { /* ignore */ }
  };

  if (context) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setContext(null)}
          className="text-indigo-600 text-sm hover:underline"
        >
          ← Back to list
        </button>
        <StepProcessingPanel
          context={context}
          onRefresh={async () => {
            try {
              if (context.wip_type === "unit") {
                setContext(await fetchUnitStepContext(context.wip.id));
              } else {
                setContext(await fetchLotStepContext(context.wip.id));
              }
            } catch { /* ignore */ }
          }}
        />
      </div>
    );
  }

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["units"] });
    queryClient.invalidateQueries({ queryKey: ["lots"] });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Active WIP</h2>
        <button onClick={refresh} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
          <ArrowPathIcon className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">View</label>
          <select value={view} onChange={(e) => setView(e.target.value as "units" | "lots")} className="input-field">
            <option value="units">Units</option>
            <option value="lots">Lots</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field">
            <option value="">All</option>
            <option value="queued">Queued</option>
            <option value="in_process">In Process</option>
            <option value="on_hold">On Hold</option>
            <option value="completed">Completed</option>
            <option value="scrapped">Scrapped</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        {view === "units" ? (
          unitsLoading ? (
            <p className="p-5 text-gray-400">Loading…</p>
          ) : !units || units.length === 0 ? (
            <p className="p-5 text-gray-400">No units found</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 px-3">Serial #</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Current Step</th>
                  <th className="py-2 px-3">Order</th>
                  <th className="py-2 px-3">Created</th>
                  <th className="py-2 px-3"></th>
                </tr>
              </thead>
              <tbody>
                {units.map((u) => (
                  <tr key={u.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-3 font-mono">{u.serial_number}</td>
                    <td className="py-2 px-3"><StatusBadge status={u.status} /></td>
                    <td className="py-2 px-3 text-sm">{u.current_step_name ?? "—"}</td>
                    <td className="py-2 px-3 font-mono text-xs">{u.order_id.slice(0, 8)}</td>
                    <td className="py-2 px-3 text-xs text-gray-400">{new Date(u.created_at).toLocaleString()}</td>
                    <td className="py-2 px-3">
                      <button onClick={() => openContext("unit", u.id)} className="text-indigo-600 text-xs hover:underline">
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : (
          lotsLoading ? (
            <p className="p-5 text-gray-400">Loading…</p>
          ) : !lots || lots.length === 0 ? (
            <p className="p-5 text-gray-400">No lots found</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 px-3">Lot #</th>
                  <th className="py-2 px-3">Qty</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Current Step</th>
                  <th className="py-2 px-3">Order</th>
                  <th className="py-2 px-3">Created</th>
                  <th className="py-2 px-3"></th>
                </tr>
              </thead>
              <tbody>
                {lots.map((l) => (
                  <tr key={l.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-3 font-mono">{l.lot_number}</td>
                    <td className="py-2 px-3">{l.quantity}</td>
                    <td className="py-2 px-3"><StatusBadge status={l.status} /></td>
                    <td className="py-2 px-3 text-sm">{l.current_step_name ?? "—"}</td>
                    <td className="py-2 px-3 font-mono text-xs">{l.order_id.slice(0, 8)}</td>
                    <td className="py-2 px-3 text-xs text-gray-400">{new Date(l.created_at).toLocaleString()}</td>
                    <td className="py-2 px-3">
                      <button onClick={() => openContext("lot", l.id)} className="text-indigo-600 text-xs hover:underline">
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
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
