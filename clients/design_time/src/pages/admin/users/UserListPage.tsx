/**
 * USER LIST PAGE — admin CRUD editor for MES users.
 * Only visible/functional when authMode !== "none".
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PlusIcon, PencilSquareIcon, TrashIcon, UserCircleIcon, DocumentDuplicateIcon } from "@heroicons/react/24/outline";
import { listUsers, deleteUser, listRoles, createUser, assignRole, type UserRead } from "../../../api/auth";
import UserFormDialog from "./UserFormDialog";
import CloneDialog from "../../../components/CloneDialog";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function UserListPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<UserRead | null | undefined>(undefined); // undefined = closed
  const [cloneTarget, setCloneTarget] = useState<UserRead | null>(null);

  const { data: users = [], isLoading, error } = useQuery({
    queryKey: ["auth-users"],
    queryFn: listUsers,
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["auth-roles"],
    queryFn: listRoles,
  });

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["auth-users"] }),
  });

  function handleDelete(user: UserRead) {
    if (confirm(`Delete user "${user.username}"? This cannot be undone.`)) {
      deleteMut.mutate(user.id);
    }
  }

  async function handleCloneUser(newUsername: string, password?: string) {
    const source = cloneTarget!;
    const newUser = await createUser({
      username: newUsername,
      email: source.email ?? undefined,
      full_name: source.full_name ?? undefined,
      password: password ?? "",
    });
    // Copy roles from source user
    for (const roleName of source.roles) {
      const role = roles.find((r) => r.name === roleName);
      if (role) await assignRole(newUser.id, role.id);
    }
    qc.invalidateQueries({ queryKey: ["auth-users"] });
    setCloneTarget(null);
  }

  function handleSaved() {
    setEditing(undefined);
    qc.invalidateQueries({ queryKey: ["auth-users"] });
  }

  return (
    <div className="p-6 space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Users</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Manage MES user accounts and role assignments.
          </p>
        </div>
        <button
          onClick={() => setEditing(null)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New User
        </button>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-x-auto">
        {isLoading ? (
          <p className="px-4 py-6 text-sm text-gray-500">Loading…</p>
        ) : error ? (
          <p className="px-4 py-6 text-sm text-red-600">Failed to load users.</p>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-gray-400">
            <UserCircleIcon className="h-10 w-10 mb-2" />
            <p className="text-sm">No users yet.</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Username
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Full Name
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Email
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Roles
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Login
                </th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-900">
                    {user.username}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-600">
                    {user.full_name ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-600">
                    {user.email ?? "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.length === 0 ? (
                        <span className="text-xs text-gray-400">none</span>
                      ) : (
                        user.roles.map((r) => (
                          <span
                            key={r}
                            className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                          >
                            {r}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {formatDate(user.last_login)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="inline-flex items-center gap-1">
                      <button
                        onClick={() => setCloneTarget(user)}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="Clone"
                      >
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditing(user)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-indigo-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(user)}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Delete"
                        disabled={deleteMut.isPending}
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
        <UserFormDialog
          user={editing}
          roles={roles}
          onClose={() => setEditing(undefined)}
          onSaved={handleSaved}
        />
      )}

      {/* Clone dialog — requires new username + password */}
      {cloneTarget && (
        <CloneDialog
          title={`Clone User — ${cloneTarget.username}`}
          label="New Username"
          initialValue={cloneTarget.username}
          secondaryField={{ key: "password", label: "Password", type: "password", placeholder: "Set a password for the new user" }}
          onClose={() => setCloneTarget(null)}
          onConfirm={handleCloneUser}
        />
      )}
    </div>
  );
}
