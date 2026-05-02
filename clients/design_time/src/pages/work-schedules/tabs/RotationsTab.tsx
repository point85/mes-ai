/**
 * Rotations Tab — CRUD for WorkRotations and their Segments.
 */

import { useState } from "react";
import { PlusIcon, TrashIcon, PencilSquareIcon, ChevronDownIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import {
  useCreateRotation,
  useUpdateRotation,
  useDeleteRotation,
  useAddRotationSegment,
  useDeleteRotationSegment,
} from "../../../hooks/useWorkSchedule";
import type { WorkRotationRead, WorkShiftRead, WorkRotationCreate, RotationSegmentCreate } from "../../../types";

interface Props {
  scheduleId: string;
  rotations: WorkRotationRead[];
  shifts: WorkShiftRead[];
}

function RotationFormDialog({ initial, onSave, onClose, saving }: {
  initial?: WorkRotationRead;
  onSave: (b: WorkRotationCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ name: name.trim(), description: description.trim() || null });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">{initial ? "Edit Rotation" : "New Rotation"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={description} onChange={(e) => setDescription(e.target.value)} />
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

function SegmentFormDialog({ shifts, nextSeq, onSave, onClose, saving }: {
  shifts: WorkShiftRead[];
  nextSeq: number;
  onSave: (b: RotationSegmentCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const [shiftId, setShiftId] = useState(shifts[0]?.id ?? "");
  const [daysOn, setDaysOn] = useState(5);
  const [daysOff, setDaysOff] = useState(2);
  const [sequence, setSequence] = useState(nextSeq);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ shift_id: shiftId, days_on: daysOn, days_off: daysOff, sequence });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Add Rotation Segment</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Shift *</label>
            <select className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={shiftId} onChange={(e) => setShiftId(e.target.value)} required>
              {shifts.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="flex gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Days On</label>
              <input type="number" min={1} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm" value={daysOn} onChange={(e) => setDaysOn(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Days Off</label>
              <input type="number" min={0} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm" value={daysOff} onChange={(e) => setDaysOff(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sequence</label>
              <input type="number" min={1} className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm" value={sequence} onChange={(e) => setSequence(Number(e.target.value))} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
            <button type="submit" disabled={saving || !shiftId} className="px-4 py-2 rounded-md bg-indigo-600 text-sm font-medium text-white disabled:opacity-50">{saving ? "Saving…" : "Add"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function RotationsTab({ scheduleId, rotations, shifts }: Props) {
  const createMut = useCreateRotation(scheduleId);
  const updateMut = useUpdateRotation(scheduleId);
  const deleteMut = useDeleteRotation(scheduleId);

  const [editing, setEditing] = useState<WorkRotationRead | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [addingSegmentFor, setAddingSegmentFor] = useState<WorkRotationRead | null>(null);

  const addSegMut = useAddRotationSegment(scheduleId, addingSegmentFor?.id ?? "");
  const delSegMut = useDeleteRotationSegment(scheduleId, addingSegmentFor?.id ?? "");

  const handleSave = (body: WorkRotationCreate) => {
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
          <PlusIcon className="h-4 w-4" /> New Rotation
        </button>
      </div>

      {rotations.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-8">No rotations defined.</p>
      )}

      <div className="space-y-2">
        {rotations.map((rotation) => {
          const expanded = expandedId === rotation.id;
          const nextSeq = Math.max(0, ...rotation.segments.map((s) => s.sequence)) + 1;
          return (
            <div key={rotation.id} className="rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center gap-3 px-4 py-3">
                <button onClick={() => setExpandedId(expanded ? null : rotation.id)} className="text-gray-400 hover:text-gray-600">
                  {expanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
                </button>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-gray-900 text-sm">{rotation.name}</span>
                  {rotation.description && <span className="ml-2 text-xs text-gray-400">{rotation.description}</span>}
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 rounded px-2 py-0.5">{rotation.day_count} days</span>
                <div className="flex gap-1">
                  <button onClick={() => setEditing(rotation)} className="p-1 text-gray-400 hover:text-indigo-600"><PencilSquareIcon className="h-4 w-4" /></button>
                  <button onClick={() => { if (confirm(`Delete rotation "${rotation.name}"?`)) deleteMut.mutate(rotation.id); }} className="p-1 text-gray-400 hover:text-red-600"><TrashIcon className="h-4 w-4" /></button>
                </div>
              </div>

              {expanded && (
                <div className="border-t border-gray-100 px-8 py-3 bg-gray-50 space-y-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Segments</span>
                    <button
                      onClick={() => setAddingSegmentFor(rotation)}
                      className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50 border border-indigo-200"
                      disabled={shifts.length === 0}
                    >
                      <PlusIcon className="h-3 w-3" /> Add Segment
                    </button>
                  </div>
                  {shifts.length === 0 && <p className="text-xs text-amber-600">Define shifts first before adding segments.</p>}
                  {rotation.segments.length === 0 && <p className="text-xs text-gray-400">No segments.</p>}
                  {[...rotation.segments].sort((a, b) => a.sequence - b.sequence).map((seg) => (
                    <div key={seg.id} className="flex items-center gap-3 text-sm">
                      <span className="text-xs text-gray-400 w-4">#{seg.sequence}</span>
                      <span className="font-medium text-gray-800">{seg.shift_name}</span>
                      <span className="text-xs text-gray-500">{seg.days_on} on / {seg.days_off} off</span>
                      <button
                        onClick={() => {
                          setAddingSegmentFor(rotation);
                          delSegMut.mutate(seg.id);
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
        <RotationFormDialog
          initial={editing ?? undefined}
          onSave={handleSave}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          saving={createMut.isPending || updateMut.isPending}
        />
      )}

      {addingSegmentFor && (
        <SegmentFormDialog
          shifts={shifts}
          nextSeq={Math.max(0, ...addingSegmentFor.segments.map((s) => s.sequence)) + 1}
          onSave={(body) => addSegMut.mutate(body, { onSuccess: () => setAddingSegmentFor(null) })}
          onClose={() => setAddingSegmentFor(null)}
          saving={addSegMut.isPending}
        />
      )}
    </div>
  );
}
