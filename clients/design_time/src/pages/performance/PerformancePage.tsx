/**
 * Performance Dashboard — equipment state log, production counters, and OEE display.
 */

import { useState } from "react";
import { PlusIcon } from "@heroicons/react/24/outline";
import { useEquipmentStates, useCounters } from "../../hooks/usePerformance";
import StateChangeFormDialog from "./StateChangeFormDialog";
import CounterFormDialog from "./CounterFormDialog";

const catColors: Record<string, string> = {
  available: "bg-green-50 text-green-700",
  busy: "bg-amber-50 text-amber-700",
  unavailable_planned: "bg-blue-50 text-blue-700",
  unavailable_unplanned: "bg-red-50 text-red-700",
};

export default function PerformancePage() {
  const [showStateForm, setShowStateForm] = useState(false);
  const [showCounterForm, setShowCounterForm] = useState(false);

  const { data: statesData, isLoading: statesLoading, error: statesError } =
    useEquipmentStates();
  const { data: countersData, isLoading: countersLoading, error: countersError } =
    useCounters();

  const states = statesData?.data ?? [];
  const counters = countersData?.data ?? [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Performance Analysis
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Track equipment state changes, production counters, and OEE metrics.
        </p>
      </div>

      {/* ─── Equipment State Logs ───────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            Equipment State Log
          </h2>
          <button
            onClick={() => setShowStateForm(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            Record State
          </button>
        </div>

        {statesLoading && (
          <p className="text-sm text-gray-500">Loading state logs…</p>
        )}
        {statesError && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            Failed to load equipment states. Is the server running?
          </div>
        )}

        {!statesLoading && !statesError && (
          <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Equipment
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    State
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    OEE Bucket
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Started
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Ended
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {states.map((s) => (
                  <tr
                    key={s.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-900">
                      {s.equipment_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {s.state}
                      {s.sub_state && (
                        <span className="text-gray-400 ml-1">
                          / {s.sub_state}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          catColors[s.dispatch_category] ??
                          "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {s.dispatch_category.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-600">
                      {s.oee_bucket.replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">
                      {s.ended_at
                        ? new Date(s.ended_at).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                ))}
                {states.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-sm text-gray-400"
                    >
                      No equipment state logs found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ─── Production Counters ────────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            Production Counters
          </h2>
          <button
            onClick={() => setShowCounterForm(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            Record Counter
          </button>
        </div>

        {countersLoading && (
          <p className="text-sm text-gray-500">Loading counters…</p>
        )}
        {countersError && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            Failed to load counters. Is the server running?
          </div>
        )}

        {!countersLoading && !countersError && (
          <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Equipment
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Shift Date
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Good
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Reject
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Rework
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Cycle (s)
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Run Time (s)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {counters.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-900">
                      {c.equipment_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {c.shift_date}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-green-700">
                      {c.good_count}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-red-600">
                      {c.reject_count}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-amber-600">
                      {c.rework_count}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">
                      {c.ideal_cycle_time_sec ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">
                      {c.actual_run_time_sec ?? "—"}
                    </td>
                  </tr>
                ))}
                {counters.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-4 py-8 text-center text-sm text-gray-400"
                    >
                      No production counters found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Dialogs */}
      {showStateForm && (
        <StateChangeFormDialog onClose={() => setShowStateForm(false)} />
      )}
      {showCounterForm && (
        <CounterFormDialog onClose={() => setShowCounterForm(false)} />
      )}
    </div>
  );
}
