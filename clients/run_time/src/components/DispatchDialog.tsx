/**
 * DispatchDialog — evaluates dispatch strategies for a queued unit or lot.
 *
 * Shows ALL candidate equipment with dispatch-relevant attributes:
 *   • Dispatch category (equipment state / availability)
 *   • Material setup (capability_match)
 *   • Queue depth vs capacity (shortest_queue / capacity)
 *   • Strategy score & rank (after Evaluate)
 *   • Eligibility status with reason for excluded equipment
 *
 * Eligible equipment rows are selectable; excluded rows are dimmed.
 */

import { useState, useEffect } from "react";
import { XMarkIcon, PlayIcon, CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";
import { fetchDispatchStrategies, evaluateDispatch } from "../api/runtime";
import type { DispatchStrategyInfo, DispatchOption, DispatchEvaluateResponse } from "../types";

interface Props {
  wipType: "unit" | "lot";
  wipId: string;
  wipLabel: string;
  onClose: () => void;
}

const STRATEGY_LABELS: Record<string, string> = {
  manual: "Manual",
  first_available: "First Available",
  shortest_queue: "Shortest Queue",
  round_robin: "Round Robin",
  capability_match: "Capability Match",
  custom: "Custom (AI)",
};

const CATEGORY_COLORS: Record<string, string> = {
  available: "bg-green-100 text-green-700",
  idle:      "bg-blue-100 text-blue-700",
  running:   "bg-yellow-100 text-yellow-700",
  faulted:   "bg-red-100 text-red-700",
  offline:   "bg-gray-100 text-gray-500",
};

function CategoryBadge({ category }: { category: string | null }) {
  if (!category) return <span className="text-gray-400 text-xs">—</span>;
  const cls = CATEGORY_COLORS[category] ?? "bg-gray-100 text-gray-500";
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${cls}`}>
      {category}
    </span>
  );
}

function QueueBar({ depth, max }: { depth: number; max: number | null }) {
  if (max == null) return <span className="tabular-nums">{depth} / ∞</span>;
  const pct = Math.min(100, (depth / max) * 100);
  const color = pct >= 100 ? "bg-red-400" : pct >= 75 ? "bg-amber-400" : "bg-indigo-400";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-14 h-1.5 rounded-full bg-gray-200 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular-nums text-xs">{depth}/{max}</span>
    </div>
  );
}

export default function DispatchDialog({ wipType, wipId, wipLabel, onClose }: Props) {
  const [strategies, setStrategies] = useState<DispatchStrategyInfo[]>([]);
  const [strategy, setStrategy] = useState<string>("");
  const [result, setResult] = useState<DispatchEvaluateResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const strats = await fetchDispatchStrategies();
        if (cancelled) return;
        setStrategies(strats);

        setLoading(true);
        const res = await evaluateDispatch(
          wipType === "unit" ? { unit_id: wipId } : { lot_id: wipId },
        );
        if (cancelled) return;
        setResult(res);
        setStrategy(res.strategy);
        setSelectedId(res.recommended?.equipment_id ?? null);
      } catch (e: unknown) {
        if (!cancelled) setError((e as { message?: string })?.message ?? "Evaluation failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    init();
    return () => { cancelled = true; };
  }, [wipType, wipId]);

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);
    try {
      const body = wipType === "unit"
        ? { unit_id: wipId, strategy: strategy || null }
        : { lot_id: wipId, strategy: strategy || null };
      const res = await evaluateDispatch(body);
      setResult(res);
      setSelectedId(res.recommended?.equipment_id ?? null);
    } catch (e: unknown) {
      setError((e as { message?: string })?.message ?? "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  // All equipment: eligible (ranked) first, then excluded
  const allEquipment: DispatchOption[] = result
    ? [
        ...[...result.options].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)),
        ...result.excluded_options,
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-3xl rounded-xl bg-white shadow-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Dispatch Evaluation</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {wipType === "unit" ? "Unit" : "Lot"}:{" "}
              <span className="font-mono font-medium">{wipLabel}</span>
            </p>
          </div>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Strategy selector */}
        <div className="px-5 py-4 border-b">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Strategy</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                disabled={loading}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
              >
                {strategies.map((s) => (
                  <option key={s.name} value={s.name}>
                    {STRATEGY_LABELS[s.name] ?? s.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleEvaluate}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 shrink-0"
            >
              <PlayIcon className="h-4 w-4" />
              {loading ? "Evaluating…" : "Evaluate"}
            </button>
          </div>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          {result?.blocked && (
            <div className="mt-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
              <span className="font-medium">Blocked:</span>{" "}
              {result.blocked_reason ?? "No eligible equipment found"}
            </div>
          )}
        </div>

        {/* Equipment table */}
        <div className="flex-1 overflow-auto">
          {loading && !result && (
            <p className="text-sm text-gray-400 py-8 text-center">Evaluating…</p>
          )}
          {!loading && result && allEquipment.length === 0 && (
            <p className="text-sm text-gray-400 py-8 text-center">No equipment found for this step.</p>
          )}
          {allEquipment.length > 0 && (
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 border-b">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="py-2 px-3 w-6"></th>
                  <th className="py-2 px-3">Equipment</th>
                  <th className="py-2 px-3">Work Cell</th>
                  <th className="py-2 px-3">State</th>
                  <th className="py-2 px-3 text-center">Material Setup</th>
                  <th className="py-2 px-3">Queue / Cap</th>
                  <th className="py-2 px-3 text-right">Score</th>
                  <th className="py-2 px-3">Notes</th>
                </tr>
              </thead>
              <tbody>
                {allEquipment.map((opt) => {
                  const isSelected = opt.equipment_id === selectedId;
                  const isRecommended = opt.equipment_id === result!.recommended?.equipment_id;
                  const isEligible = opt.eligible;

                  return (
                    <tr
                      key={opt.equipment_id}
                      onClick={() => isEligible && setSelectedId(opt.equipment_id)}
                      className={`border-b transition-colors ${
                        !isEligible
                          ? "opacity-45 bg-gray-50 cursor-not-allowed"
                          : isSelected
                          ? "bg-indigo-50 ring-1 ring-inset ring-indigo-300 cursor-pointer"
                          : "hover:bg-gray-50 cursor-pointer"
                      }`}
                    >
                      {/* Recommended indicator / ineligible icon */}
                      <td className="py-2 px-3">
                        {isEligible && isRecommended ? (
                          <span className="inline-block w-2 h-2 rounded-full bg-indigo-500" title="Recommended" />
                        ) : !isEligible ? (
                          <XCircleIcon className="h-3.5 w-3.5 text-gray-300" />
                        ) : isSelected ? (
                          <CheckCircleIcon className="h-3.5 w-3.5 text-indigo-500" />
                        ) : null}
                      </td>

                      {/* Equipment */}
                      <td className="py-2 px-3">
                        <span className="font-mono font-medium">{opt.equipment_code}</span>
                        {opt.equipment_name && (
                          <span className="ml-1 text-gray-500 font-normal">{opt.equipment_name}</span>
                        )}
                      </td>

                      {/* Work cell */}
                      <td className="py-2 px-3 text-gray-600">
                        <div className="font-mono text-xs">{opt.work_cell_code}</div>
                        {opt.work_cell_name && (
                          <div className="text-gray-400 text-xs">{opt.work_cell_name}</div>
                        )}
                      </td>

                      {/* Dispatch category (state) */}
                      <td className="py-2 px-3">
                        <CategoryBadge category={opt.dispatch_category} />
                      </td>

                      {/* Material setup */}
                      <td className="py-2 px-3 text-center">
                        {opt.material_setup ? (
                          <CheckCircleIcon className="h-4 w-4 text-green-500 inline-block" title="Set up" />
                        ) : (
                          <XCircleIcon className="h-4 w-4 text-red-400 inline-block" title="Not set up" />
                        )}
                      </td>

                      {/* Queue depth */}
                      <td className="py-2 px-3">
                        <QueueBar depth={opt.queue_depth} max={opt.max_queue_depth} />
                      </td>

                      {/* Score */}
                      <td className="py-2 px-3 text-right tabular-nums font-medium">
                        {isEligible ? opt.score.toFixed(1) : "—"}
                      </td>

                      {/* Notes / reason */}
                      <td className="py-2 px-3 text-xs text-gray-500">
                        {opt.reason ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

