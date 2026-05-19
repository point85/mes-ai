/**
 * Work Schedule List Page — table of schedules with create/edit/delete.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlusIcon, TrashIcon, PencilSquareIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import {
  useWorkSchedules,
  useCreateWorkSchedule,
  useUpdateWorkSchedule,
  useDeleteWorkSchedule,
} from "../../hooks/useWorkSchedule";
import type { WorkScheduleSummary, WorkScheduleCreate } from "../../types";
import WorkScheduleFormDialog from "./WorkScheduleFormDialog";

export default function WorkScheduleListPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useWorkSchedules();
  const createMut = useCreateWorkSchedule();
  const updateMut = useUpdateWorkSchedule();
  const deleteMut = useDeleteWorkSchedule();

  const [editing, setEditing] = useState<WorkScheduleSummary | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const schedules = data?.data ?? [];

  const handleDelete = (s: WorkScheduleSummary) => {
    if (!confirm(`Delete work schedule "${s.name}"?`)) return;
    deleteMut.mutate(s.id);
  };

  const handleSave = (body: WorkScheduleCreate) => {
    if (editing) {
      updateMut.mutate({ id: editing.id, ...body }, { onSuccess: () => setEditing(null) });
    } else {
      createMut.mutate(body, { onSuccess: () => setShowCreate(false) });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Work Schedules</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define shifts, rotations, teams, and non-working periods.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Schedule
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading schedules…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">
          Failed to load work schedules.
        </div>
      )}

      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Description</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Shifts</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Teams</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {schedules.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                    No work schedules defined yet.
                  </td>
                </tr>
              )}
              {schedules.map((s) => (
                <tr
                  key={s.id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/work-schedules/${s.id}`)}
                >
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-900">{s.name}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">{s.description ?? "—"}</td>
                  <td className="px-4 py-2.5 text-center text-sm text-gray-700">{s.shift_count}</td>
                  <td className="px-4 py-2.5 text-center text-sm text-gray-700">{s.team_count}</td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => navigate(`/work-schedules/${s.id}`)}
                        className="p-1 text-gray-400 hover:text-indigo-600 transition-colors"
                        title="Open detail"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditing(s)}
                        className="p-1 text-gray-400 hover:text-indigo-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(s)}
                        className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showCreate || editing) && (
        <WorkScheduleFormDialog
          initial={editing ?? undefined}
          onSave={handleSave}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          saving={createMut.isPending || updateMut.isPending}
        />
      )}

    </div>
  );
}
