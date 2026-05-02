/**
 * Shift Instances Dialog — date/time range picker that displays all shift
 * instances for a work schedule along with working / non-working time totals.
 */

import { useState } from "react";
import { useShiftInstancesForRange, useWorkingTime } from "../../hooks/useWorkSchedule";

interface Props {
  scheduleId: string;
  scheduleName: string;
  onClose: () => void;
}

function fmtSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h} h ${m} min`;
}

function fmtDT(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function toDateTimeLocalStr(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function ShiftInstancesDialog({ scheduleId, scheduleName, onClose }: Props) {
  const defaultFrom = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return toDateTimeLocalStr(d); };
  const defaultTo   = () => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + 7); return toDateTimeLocalStr(d); };

  const [fromDt, setFromDt] = useState(defaultFrom);
  const [toDt,   setToDt]   = useState(defaultTo);
  const [query,  setQuery]  = useState<{ from: string; to: string } | null>(null);

  const rangeQuery = useShiftInstancesForRange(
    scheduleId,
    query ? query.from.slice(0, 10) : "",
    query ? query.to.slice(0, 10) : "",
  );
  const workTimeQuery = useWorkingTime(
    scheduleId,
    query ? query.from + ":00" : "",
    query ? query.to + ":00" : "",
  );

  const instances   = rangeQuery.data?.data ?? [];
  const workingSec  = workTimeQuery.data?.working_seconds ?? 0;
  const periodSec   = query
    ? (new Date(query.to + ":00").getTime() - new Date(query.from + ":00").getTime()) / 1000
    : 0;
  const nonWorkingSec = Math.max(0, periodSec - workingSec);
  const loading = rangeQuery.isFetching || workTimeQuery.isFetching;
  const hasData = query !== null && !loading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-4xl rounded-lg bg-white shadow-xl p-6 flex flex-col gap-4 max-h-[90vh]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Shift Instances — {scheduleName}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        {/* Date/time range pickers */}
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
            <input
              type="datetime-local"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              value={fromDt}
              onChange={(e) => setFromDt(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
            <input
              type="datetime-local"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              value={toDt}
              onChange={(e) => setToDt(e.target.value)}
            />
          </div>
          <button
            onClick={() => setQuery({ from: fromDt, to: toDt })}
            disabled={!fromDt || !toDt || fromDt >= toDt}
            className="px-4 py-2 rounded-md bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            Show Shifts
          </button>
        </div>

        {/* Summary bar */}
        {query && !loading && (
          <div className="flex gap-8 rounded-lg bg-indigo-50 border border-indigo-100 px-4 py-3 text-sm">
            <div>
              <span className="text-gray-500">Working time:</span>{" "}
              <span className="font-semibold text-indigo-900">{fmtSeconds(workingSec)}</span>
            </div>
            <div>
              <span className="text-gray-500">Non-working time:</span>{" "}
              <span className="font-semibold text-indigo-900">{fmtSeconds(nonWorkingSec)}</span>
            </div>
          </div>
        )}

        {/* Instances table */}
        <div className="overflow-auto flex-1 min-h-0">
          {loading && (
            <p className="text-sm text-gray-500 text-center py-8">Loading…</p>
          )}
          {hasData && instances.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">No shift instances in the selected period.</p>
          )}
          {hasData && instances.length > 0 && (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 sticky top-0">
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Shift</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Start</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">End</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Team</th>
                </tr>
              </thead>
              <tbody>
                {instances.map((inst, idx) => (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-3 py-2 text-gray-900 font-medium">{inst.shift_name}</td>
                    <td className="px-3 py-2 text-gray-700 font-mono text-xs">{fmtDT(inst.start_datetime)}</td>
                    <td className="px-3 py-2 text-gray-700 font-mono text-xs">{fmtDT(inst.end_datetime)}</td>
                    <td className="px-3 py-2 text-gray-700">{inst.team_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="flex justify-end pt-1">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Close</button>
        </div>
      </div>
    </div>
  );
}
