/**
 * Non-Working Periods Tab — CRUD for schedule holidays/blackouts.
 */

import { useState } from "react";
import { PlusIcon, TrashIcon, PencilSquareIcon } from "@heroicons/react/24/outline";
import {
  useCreateNonWorkingPeriod,
  useUpdateNonWorkingPeriod,
  useDeleteNonWorkingPeriod,
} from "../../../hooks/useWorkSchedule";
import type { NonWorkingPeriodRead, NonWorkingPeriodCreate } from "../../../types";

interface Props {
  scheduleId: string;
  periods: NonWorkingPeriodRead[];
}

function formatDuration(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  return parts.length > 0 ? parts.join(" ") : "< 1h";
}

function NWPFormDialog({ initial, onSave, onClose, saving }: {
  initial?: NonWorkingPeriodRead;
  onSave: (b: NonWorkingPeriodCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const parseStart = (dt?: string) => dt ? dt.slice(0, 16) : new Date().toISOString().slice(0, 16);

  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [startDt, setStartDt] = useState(parseStart(initial?.start_datetime));
  const [days, setDays] = useState(initial ? Math.floor(initial.duration_seconds / 86400) : 1);
  const [hours, setHours] = useState(initial ? Math.floor((initial.duration_seconds % 86400) / 3600) : 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      name: name.trim(),
      description: description.trim() || null,
      start_datetime: `${startDt}:00`,
      duration_seconds: days * 86400 + hours * 3600,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">{initial ? "Edit Period" : "New Non-Working Period"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Date/Time *</label>
            <input type="datetime-local" className="rounded-md border border-gray-300 px-3 py-2 text-sm" value={startDt} onChange={(e) => setStartDt(e.target.value)} required />
          </div>
          <div className="flex gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Days</label>
              <input type="number" min={0} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hours</label>
              <input type="number" min={0} max={23} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm" value={hours} onChange={(e) => setHours(Number(e.target.value))} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-md bg-indigo-600 text-sm font-medium text-white disabled:opacity-50">{saving ? "Saving…" : "Save"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function NonWorkingPeriodsTab({ scheduleId, periods }: Props) {
  const createMut = useCreateNonWorkingPeriod(scheduleId);
  const updateMut = useUpdateNonWorkingPeriod(scheduleId);
  const deleteMut = useDeleteNonWorkingPeriod(scheduleId);

  const [editing, setEditing] = useState<NonWorkingPeriodRead | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const handleSave = (body: NonWorkingPeriodCreate) => {
    if (editing) {
      updateMut.mutate({ id: editing.id, ...body }, { onSuccess: () => setEditing(null) });
    } else {
      createMut.mutate(body, { onSuccess: () => setShowCreate(false) });
    }
  };

  const sorted = [...periods].sort((a, b) => a.start_datetime.localeCompare(b.start_datetime));

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500">
          <PlusIcon className="h-4 w-4" /> Add Period
        </button>
      </div>

      {periods.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-8">No non-working periods defined.</p>
      )}

      {sorted.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Start</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">End</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Duration</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {sorted.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-900">
                    {p.name}
                    {p.description && <span className="ml-2 text-xs text-gray-400">{p.description}</span>}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-600 font-mono">{p.start_datetime.slice(0, 16).replace("T", " ")}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-600 font-mono">{p.end_datetime.slice(0, 16).replace("T", " ")}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">{formatDuration(p.duration_seconds)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => setEditing(p)} className="p-1 text-gray-400 hover:text-indigo-600"><PencilSquareIcon className="h-4 w-4" /></button>
                      <button onClick={() => { if (confirm(`Delete period "${p.name}"?`)) deleteMut.mutate(p.id); }} className="p-1 text-gray-400 hover:text-red-600"><TrashIcon className="h-4 w-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showCreate || editing) && (
        <NWPFormDialog
          initial={editing ?? undefined}
          onSave={handleSave}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          saving={createMut.isPending || updateMut.isPending}
        />
      )}
    </div>
  );
}
