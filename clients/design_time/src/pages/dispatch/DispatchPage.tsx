/**
 * DispatchPage — dispatch evaluation, execution, strategies list, and queue viewer.
 */

import { useState, useMemo } from "react";
import {
  PlayIcon,
  ArrowPathIcon,
  QueueListIcon,
} from "@heroicons/react/24/outline";
import {
  useDispatchStrategies,
  useDispatchQueue,
  useEvaluateDispatch,
  useExecuteDispatch,
} from "../../hooks/useDispatch";
import type { DispatchOption, DispatchStrategyInfo, DispatchQueueItem } from "../../types/dispatch";

export default function DispatchPage() {
  // Evaluate form state
  const [unitId, setUnitId] = useState("");
  const [lotId, setLotId] = useState("");
  const [strategy, setStrategy] = useState("");
  const [options, setOptions] = useState<DispatchOption[]>([]);

  // Queue filter
  const [queueWc, setQueueWc] = useState("default");

  const { data: strategies = [] } = useDispatchStrategies();
  const { data: queue = [], isLoading: queueLoading } =
    useDispatchQueue(queueWc);

  const evaluateMutation = useEvaluateDispatch();
  const executeMutation = useExecuteDispatch();

  const handleEvaluate = async () => {
    const body: any = {};
    if (unitId.trim()) body.unit_id = unitId.trim();
    if (lotId.trim()) body.lot_id = lotId.trim();
    if (strategy) body.strategy = strategy;
    const res = await evaluateMutation.mutateAsync(body);
    setOptions(res.options ?? []);
  };

  const handleExecute = async (opt: DispatchOption) => {
    await executeMutation.mutateAsync({
      unit_id: unitId.trim() || undefined,
      lot_id: lotId.trim() || undefined,
      destination_equipment_id: opt.equipment_id,
      destination_step_id: opt.step_id,
    });
    setOptions([]);
    setUnitId("");
    setLotId("");
  };

  // Sorted options by score descending
  const sortedOptions = useMemo(
    () => [...options].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)),
    [options],
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dispatch</h1>
        <p className="text-sm text-gray-500 mt-1">
          Evaluate dispatch options, execute assignments, and monitor the queue.
        </p>
      </div>

      {/* ─── Strategies ─────────────────────────────────────────── */}
      {strategies.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-gray-800">
            Available Strategies
          </h2>
          <div className="flex flex-wrap gap-2">
            {strategies.map((s: DispatchStrategyInfo) => (
              <span
                key={s.name}
                className="inline-flex items-center rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700"
              >
                {s.name}
                {s.description && (
                  <span className="ml-1 text-indigo-400">
                    — {s.description}
                  </span>
                )}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* ─── Evaluate ───────────────────────────────────────────── */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">
          Evaluate Dispatch
        </h2>
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex-1 min-w-[140px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Unit ID
            </label>
            <input
              value={unitId}
              onChange={(e) => setUnitId(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div className="flex-1 min-w-[140px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Lot ID
            </label>
            <input
              value={lotId}
              onChange={(e) => setLotId(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div className="min-w-[160px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Strategy
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            >
              <option value="">Default</option>
              {strategies.map((s: DispatchStrategyInfo) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleEvaluate}
            disabled={evaluateMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors"
          >
            <ArrowPathIcon className="h-4 w-4" />
            {evaluateMutation.isPending ? "Evaluating…" : "Evaluate"}
          </button>
        </div>

        {evaluateMutation.error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            Evaluation failed. Check the IDs and try again.
          </div>
        )}

        {/* Options results */}
        {sortedOptions.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Work Center
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Equipment
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Reason
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {sortedOptions.map((opt, i) => (
                  <tr
                    key={i}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm text-gray-900">
                      {opt.work_center_id ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-700">
                      {opt.equipment_id
                        ? `${opt.equipment_id.slice(0, 8)}…`
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-indigo-700">
                      {opt.score != null ? opt.score.toFixed(2) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {opt.reason ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={() => handleExecute(opt)}
                        disabled={executeMutation.isPending}
                        className="inline-flex items-center gap-1 rounded bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50"
                      >
                        <PlayIcon className="h-3 w-3" />
                        Execute
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ─── Queue ──────────────────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center gap-3">
          <QueueListIcon className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold text-gray-800">
            Dispatch Queue
          </h2>
          <div className="ml-auto">
            <input
              value={queueWc}
              onChange={(e) => setQueueWc(e.target.value)}
              placeholder="Filter by work center…"
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 w-56"
            />
          </div>
        </div>

        {queueLoading && (
          <p className="text-sm text-gray-500">Loading queue…</p>
        )}

        {!queueLoading && (
          <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Unit / Lot
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Work Center
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Equipment
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Queued At
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {queue.map((q: DispatchQueueItem, i: number) => (
                  <tr
                    key={i}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-900">
                      {q.unit_id ?? q.lot_id ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {q.current_step_id ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-700">
                      {q.equipment_id
                        ? `${q.equipment_id.slice(0, 8)}…`
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          q.status === "waiting"
                            ? "bg-amber-50 text-amber-700"
                            : q.status === "assigned"
                            ? "bg-blue-50 text-blue-700"
                            : q.status === "completed"
                            ? "bg-green-50 text-green-700"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {q.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {"—"}
                    </td>
                  </tr>
                ))}
                {queue.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center text-sm text-gray-400"
                    >
                      Queue is empty.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
