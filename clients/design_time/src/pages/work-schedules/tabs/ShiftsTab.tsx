/**
 * Shifts Tab — CRUD for WorkShifts within a schedule.
 */

import { useState } from "react";
import { PlusIcon, TrashIcon, PencilSquareIcon, ChevronDownIcon, ChevronRightIcon, ChartBarIcon } from "@heroicons/react/24/outline";
import { useCreateShift, useUpdateShift, useDeleteShift, useAddBreak, useDeleteBreak, useShiftInstancesForRange, useWorkingTime } from "../../../hooks/useWorkSchedule";
import type { WorkShiftRead, WorkShiftCreate, ShiftBreakCreate } from "../../../types";

interface Props {
  scheduleId: string;
  shifts: WorkShiftRead[];
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function fmtSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h} h ${m} min`;
}

function fmtDT(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function toDateTimeLocalStr(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ── Shift Statistics Dialog ──────────────────────────────────────────────────

function ShiftStatsDialog({ scheduleId, shift, onClose }: {
  scheduleId: string;
  shift: WorkShiftRead;
  onClose: () => void;
}) {
  const defaultFrom = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return toDateTimeLocalStr(d); };
  const defaultTo = () => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + 7); return toDateTimeLocalStr(d); };

  const [fromDt, setFromDt] = useState(defaultFrom);
  const [toDt, setToDt] = useState(defaultTo);
  const [query, setQuery] = useState<{ from: string; to: string } | null>(null);

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

  const allInstances = rangeQuery.data?.data ?? [];
  const shiftInstances = allInstances.filter((i) => i.shift_id === shift.id);
  const workingSec = workTimeQuery.data?.working_seconds ?? 0;
  const periodSec = query
    ? (new Date(query.to + ":00").getTime() - new Date(query.from + ":00").getTime()) / 1000
    : 0;
  const nonWorkingSec = Math.max(0, periodSec - workingSec);
  const loading = rangeQuery.isFetching || workTimeQuery.isFetching;
  const hasData = query !== null && !loading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-3xl rounded-lg bg-white shadow-xl p-6 flex flex-col gap-4 max-h-[90vh]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Shift Statistics — {shift.name}</h2>
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
          {hasData && shiftInstances.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">No shift instances for "{shift.name}" in the selected period.</p>
          )}
          {hasData && shiftInstances.length > 0 && (
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
                {shiftInstances.map((inst, idx) => (
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

// ── Shift Form ────────────────────────────────────────────────────────────────

function ShiftFormDialog({ initial, onSave, onClose, saving }: {
  initial?: WorkShiftRead;
  onSave: (b: WorkShiftCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [startTime, setStartTime] = useState(initial?.start_time?.slice(0, 5) ?? "06:00");
  const [hours, setHours] = useState(initial ? String(Math.floor(initial.duration_seconds / 3600)) : "8");
  const [minutes, setMinutes] = useState(initial ? String(Math.floor((initial.duration_seconds % 3600) / 60)) : "0");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      name: name.trim(),
      description: description.trim() || null,
      start_time: `${startTime}:00`,
      duration_seconds: (parseInt(hours, 10) || 0) * 3600 + (parseInt(minutes, 10) || 0) * 60,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">{initial ? "Edit Shift" : "New Shift"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
            <input type="time" className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          </div>
          <div className="flex gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hours</label>
              <input type="number" min={0} max={23} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" value={hours} onChange={(e) => setHours(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Minutes</label>
              <input type="number" min={0} max={59} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-md bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50">{saving ? "Saving…" : "Save"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Break Form ────────────────────────────────────────────────────────────────

function BreakFormDialog({ onSave, onClose, saving }: {
  onSave: (b: ShiftBreakCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const [name, setName] = useState("");
  const [startTime, setStartTime] = useState("10:00");
  const [minutes, setMinutes] = useState(15);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ name: name.trim(), start_time: `${startTime}:00`, duration_seconds: minutes * 60 });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Add Break</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
            <input type="time" className="rounded-md border border-gray-300 px-3 py-2 text-sm" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Duration (minutes)</label>
            <input type="number" min={1} max={120} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-md bg-indigo-600 text-sm font-medium text-white disabled:opacity-50">{saving ? "Saving…" : "Add"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ShiftsTab({ scheduleId, shifts }: Props) {
  const createMut = useCreateShift(scheduleId);
  const updateMut = useUpdateShift(scheduleId);
  const deleteMut = useDeleteShift(scheduleId);

  const [editing, setEditing] = useState<WorkShiftRead | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [addingBreakForShift, setAddingBreakForShift] = useState<string | null>(null);
  const [statsShift, setStatsShift] = useState<WorkShiftRead | null>(null);

  const addBreakMut = useAddBreak(scheduleId, addingBreakForShift ?? "");
  const deleteBreakMutFn = useDeleteBreak(scheduleId, addingBreakForShift ?? "");

  const handleSave = (body: WorkShiftCreate) => {
    if (editing) {
      updateMut.mutate({ id: editing.id, ...body }, { onSuccess: () => setEditing(null) });
    } else {
      createMut.mutate(body, { onSuccess: () => setShowCreate(false) });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500">
          <PlusIcon className="h-4 w-4" /> New Shift
        </button>
      </div>

      {shifts.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-8">No shifts defined. Click "New Shift" to add one.</p>
      )}

      <div className="space-y-2">
        {shifts.map((shift) => {
          const expanded = expandedId === shift.id;
          return (
            <div key={shift.id} className="rounded-lg border border-gray-200 bg-white shadow-sm">
              {/* Shift row */}
              <div className="flex items-center gap-3 px-4 py-3">
                <button onClick={() => setExpandedId(expanded ? null : shift.id)} className="text-gray-400 hover:text-gray-600">
                  {expanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
                </button>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-gray-900 text-sm">{shift.name}</span>
                  {shift.description && <span className="ml-2 text-xs text-gray-400">{shift.description}</span>}
                </div>
                <span className="text-xs text-gray-500 font-mono">{shift.start_time?.slice(0, 5)}</span>
                <span className="text-xs text-gray-500 bg-gray-100 rounded px-2 py-0.5">{formatDuration(shift.duration_seconds)}</span>
                <span className="text-xs text-gray-400">{shift.breaks.length} break{shift.breaks.length !== 1 ? "s" : ""}</span>
                <div className="flex gap-1">
                  <button onClick={() => setStatsShift(shift)} className="p-1 text-gray-400 hover:text-blue-600" title="Shift statistics"><ChartBarIcon className="h-4 w-4" /></button>
                  <button onClick={() => setEditing(shift)} className="p-1 text-gray-400 hover:text-indigo-600"><PencilSquareIcon className="h-4 w-4" /></button>
                  <button onClick={() => { if (confirm(`Delete shift "${shift.name}"?`)) deleteMut.mutate(shift.id); }} className="p-1 text-gray-400 hover:text-red-600"><TrashIcon className="h-4 w-4" /></button>
                </div>
              </div>

              {/* Breaks */}
              {expanded && (
                <div className="border-t border-gray-100 px-8 py-3 bg-gray-50 space-y-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Breaks</span>
                    <button
                      onClick={() => setAddingBreakForShift(shift.id)}
                      className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50 border border-indigo-200"
                    >
                      <PlusIcon className="h-3 w-3" /> Add Break
                    </button>
                  </div>
                  {shift.breaks.length === 0 && <p className="text-xs text-gray-400">No breaks.</p>}
                  {shift.breaks.map((brk) => (
                    <div key={brk.id} className="flex items-center gap-3 text-sm">
                      <span className="font-medium text-gray-800">{brk.name}</span>
                      <span className="font-mono text-xs text-gray-500">{brk.start_time?.slice(0, 5)}</span>
                      <span className="text-xs text-gray-400">{formatDuration(brk.duration_seconds)}</span>
                      <button
                        onClick={() => {
                          setAddingBreakForShift(shift.id);
                          deleteBreakMutFn.mutate(brk.id);
                        }}
                        className="ml-auto p-0.5 text-gray-300 hover:text-red-500"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {(showCreate || editing) && (
        <ShiftFormDialog
          initial={editing ?? undefined}
          onSave={handleSave}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          saving={createMut.isPending || updateMut.isPending}
        />
      )}

      {addingBreakForShift && (
        <BreakFormDialog
          onSave={(body) => addBreakMut.mutate(body, { onSuccess: () => setAddingBreakForShift(null) })}
          onClose={() => setAddingBreakForShift(null)}
          saving={addBreakMut.isPending}
        />
      )}

      {statsShift && (
        <ShiftStatsDialog
          scheduleId={scheduleId}
          shift={statsShift}
          onClose={() => setStatsShift(null)}
        />
      )}
    </div>
  );
}
