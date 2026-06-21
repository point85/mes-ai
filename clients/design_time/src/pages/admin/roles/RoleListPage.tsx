/**
 * ROLE LIST PAGE — admin CRUD editor for MES roles and their permissions.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PlusIcon, PencilSquareIcon, TrashIcon, ShieldCheckIcon, DocumentDuplicateIcon } from "@heroicons/react/24/outline";
import { listRoles, deleteRole, createRole, type RoleRead } from "../../../api/auth";
import RoleFormDialog from "./RoleFormDialog";
import CloneDialog from "../../../components/CloneDialog";

export default function RoleListPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<RoleRead | null | undefined>(undefined); // undefined = closed
  const [cloneTarget, setCloneTarget] = useState<RoleRead | null>(null);

  const { data: roles = [], isLoading, error } = useQuery({
    queryKey: ["auth-roles"],
    queryFn: listRoles,
  });

  const deleteMut = useMutation({
    mutationFn: deleteRole,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["auth-roles"] }),
  });

  function handleDelete(role: RoleRead) {
    if (confirm(`Delete role "${role.name}"? This cannot be undone.`)) {
      deleteMut.mutate(role.id);
    }
  }

  function handleSaved() {
    setEditing(undefined);
    qc.invalidateQueries({ queryKey: ["auth-roles"] });
  }

  async function handleClone(newName: string) {
    const r = cloneTarget!;
    await createRole({ name: newName, description: r.description ?? undefined });
    qc.invalidateQueries({ queryKey: ["auth-roles"] });
    setCloneTarget(null);
  }

  return (
    <div className="p-6 space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Roles</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Manage roles and their permission sets.
          </p>
        </div>
        <button
          onClick={() => setEditing(null)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Role
        </button>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-x-auto">
        {isLoading ? (
          <p className="px-4 py-6 text-sm text-gray-500">Loading…</p>
        ) : error ? (
          <p className="px-4 py-6 text-sm text-red-600">Failed to load roles.</p>
        ) : roles.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-gray-400">
            <ShieldCheckIcon className="h-10 w-10 mb-2" />
            <p className="text-sm">No roles yet.</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Description
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Permissions
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {roles.map((role) => (
                <tr key={role.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-900">{role.name}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-600">{role.description ?? "—"}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {role.permissions.length}{" "}
                    <span className="text-gray-400">
                      {role.permissions.length === 1 ? "permission" : "permissions"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    {role.is_system ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                        <ShieldCheckIcon className="h-3 w-3" />
                        System
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">Custom</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="inline-flex items-center gap-1">
                      <button
                        onClick={() => setCloneTarget(role)}
                        disabled={role.is_system}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title={role.is_system ? "System roles cannot be cloned" : "Clone"}
                      >
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditing(role)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-indigo-600 transition-colors"
                        title="View / Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(role)}
                        disabled={role.is_system || deleteMut.isPending}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                        title={role.is_system ? "System roles cannot be deleted" : "Delete"}
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create / edit dialog */}
      {editing !== undefined && (
        <RoleFormDialog
          role={editing}
          onClose={() => setEditing(undefined)}
          onSaved={handleSaved}
        />
      )}

      {/* Clone dialog */}
      {cloneTarget && (
        <CloneDialog
          title={`Clone Role — ${cloneTarget.name}`}
          label="New Name"
          initialValue={cloneTarget.name}
          onClose={() => setCloneTarget(null)}
          onConfirm={handleClone}
        />
      )}
    </div>
  );
}
