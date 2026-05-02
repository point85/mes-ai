/**
 * Teams Tab — CRUD for WorkTeams, members, and member exceptions.
 */

import { useState } from "react";
import { PlusIcon, TrashIcon, PencilSquareIcon, ChevronDownIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import {
  useCreateTeam, useUpdateTeam, useDeleteTeam,
  useAddTeamMember, useDeleteTeamMember,
} from "../../../hooks/useWorkSchedule";
import type { WorkTeamRead, WorkTeamCreate, WorkRotationRead, TeamMemberCreate } from "../../../types";

interface Props {
  scheduleId: string;
  teams: WorkTeamRead[];
  rotations: WorkRotationRead[];
}

function TeamFormDialog({ initial, rotations, onSave, onClose, saving }: {
  initial?: WorkTeamRead;
  rotations: WorkRotationRead[];
  onSave: (b: WorkTeamCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [rotationId, setRotationId] = useState(initial?.rotation_id ?? rotations[0]?.id ?? "");
  const [rotationStart, setRotationStart] = useState(initial?.rotation_start ?? new Date().toISOString().slice(0, 10));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ name: name.trim(), description: description.trim() || null, rotation_id: rotationId, rotation_start: rotationStart });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">{initial ? "Edit Team" : "New Team"}</h2>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Rotation *</label>
            <select className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={rotationId} onChange={(e) => setRotationId(e.target.value)} required>
              {rotations.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rotation Start Date *</label>
            <input type="date" className="rounded-md border border-gray-300 px-3 py-2 text-sm" value={rotationStart} onChange={(e) => setRotationStart(e.target.value)} required />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
            <button type="submit" disabled={saving || !rotationId} className="px-4 py-2 rounded-md bg-indigo-600 text-sm font-medium text-white disabled:opacity-50">{saving ? "Saving…" : "Save"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MemberFormDialog({ onSave, onClose, saving }: {
  onSave: (b: TeamMemberCreate) => void;
  onClose: () => void;
  saving?: boolean;
}) {
  const [memberId, setMemberId] = useState("");
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ member_id: memberId.trim(), name: name.trim() });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-lg bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Add Member</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID *</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={memberId} onChange={(e) => setMemberId(e.target.value)} required autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} required />
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

export default function TeamsTab({ scheduleId, teams, rotations }: Props) {
  const createMut = useCreateTeam(scheduleId);
  const updateMut = useUpdateTeam(scheduleId);
  const deleteMut = useDeleteTeam(scheduleId);

  const [editing, setEditing] = useState<WorkTeamRead | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [addingMemberFor, setAddingMemberFor] = useState<string | null>(null);

  const addMemberMut = useAddTeamMember(scheduleId, addingMemberFor ?? "");
  const delMemberMut = useDeleteTeamMember(scheduleId, addingMemberFor ?? "");

  const handleSave = (body: WorkTeamCreate) => {
    if (editing) {
      updateMut.mutate({ id: editing.id, ...body }, { onSuccess: () => setEditing(null) });
    } else {
      createMut.mutate(body, { onSuccess: () => setShowCreate(false) });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setShowCreate(true)}
          disabled={rotations.length === 0}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          title={rotations.length === 0 ? "Define rotations first" : undefined}
        >
          <PlusIcon className="h-4 w-4" /> New Team
        </button>
      </div>
      {rotations.length === 0 && (
        <p className="text-sm text-amber-600 text-center py-2">Define rotations before creating teams.</p>
      )}

      {teams.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-8">No teams defined.</p>
      )}

      <div className="space-y-2">
        {teams.map((team) => {
          const expanded = expandedId === team.id;
          return (
            <div key={team.id} className="rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center gap-3 px-4 py-3">
                <button onClick={() => setExpandedId(expanded ? null : team.id)} className="text-gray-400 hover:text-gray-600">
                  {expanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
                </button>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-gray-900 text-sm">{team.name}</span>
                  {team.description && <span className="ml-2 text-xs text-gray-400">{team.description}</span>}
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 rounded px-2 py-0.5">
                  starts {team.rotation_start}
                </span>
                <span className="text-xs text-gray-400">{team.members.length} member{team.members.length !== 1 ? "s" : ""}</span>
                <div className="flex gap-1">
                  <button onClick={() => setEditing(team)} className="p-1 text-gray-400 hover:text-indigo-600"><PencilSquareIcon className="h-4 w-4" /></button>
                  <button onClick={() => { if (confirm(`Delete team "${team.name}"?`)) deleteMut.mutate(team.id); }} className="p-1 text-gray-400 hover:text-red-600"><TrashIcon className="h-4 w-4" /></button>
                </div>
              </div>

              {expanded && (
                <div className="border-t border-gray-100 px-8 py-3 bg-gray-50 space-y-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Members</span>
                    <button
                      onClick={() => setAddingMemberFor(team.id)}
                      className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50 border border-indigo-200"
                    >
                      <PlusIcon className="h-3 w-3" /> Add Member
                    </button>
                  </div>
                  {team.members.length === 0 && <p className="text-xs text-gray-400">No members.</p>}
                  {team.members.map((m) => (
                    <div key={m.id} className="flex items-center gap-3 text-sm">
                      <span className="font-medium text-gray-800">{m.name}</span>
                      <span className="text-xs text-gray-400 font-mono">{m.member_id}</span>
                      <button
                        onClick={() => {
                          setAddingMemberFor(team.id);
                          delMemberMut.mutate(m.id);
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
        <TeamFormDialog
          initial={editing ?? undefined}
          rotations={rotations}
          onSave={handleSave}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          saving={createMut.isPending || updateMut.isPending}
        />
      )}

      {addingMemberFor && (
        <MemberFormDialog
          onSave={(body) => addMemberMut.mutate(body, { onSuccess: () => setAddingMemberFor(null) })}
          onClose={() => setAddingMemberFor(null)}
          saving={addMemberMut.isPending}
        />
      )}
    </div>
  );
}
