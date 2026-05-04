/**
 * USER FORM DIALOG — create or edit a local MES user.
 * On create: username (required), email, full_name, password (required), roles.
 * On edit:   email, full_name, password (optional reset), is_active, roles.
 */

import { useEffect, useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { createUser, updateUser, assignRole, removeRole, type UserRead, type RoleRead } from "../../../api/auth";

interface Props {
  user: UserRead | null;   // null = create mode
  roles: RoleRead[];       // available roles for assignment checkboxes
  onClose: () => void;
  onSaved: () => void;
}

export default function UserFormDialog({ user, roles, onClose, onSaved }: Props) {
  const isCreate = user === null;

  const [username, setUsername] = useState(user?.username ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [password, setPassword] = useState("");
  const [isActive, setIsActive] = useState(user?.is_active ?? true);
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set(user?.roles ?? []));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Keep selectedRoles in sync if parent re-passes user prop
  useEffect(() => {
    setSelectedRoles(new Set(user?.roles ?? []));
  }, [user]);

  function toggleRole(roleName: string) {
    setSelectedRoles((prev) => {
      const next = new Set(prev);
      if (next.has(roleName)) next.delete(roleName);
      else next.add(roleName);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      let savedUser: UserRead;
      if (isCreate) {
        savedUser = await createUser({
          username,
          email: email || undefined,
          full_name: fullName || undefined,
          password,
        });
      } else {
        savedUser = await updateUser(user!.id, {
          email: email || undefined,
          full_name: fullName || undefined,
          is_active: isActive,
          password: password || undefined,
        });
      }

      // Reconcile roles: assign new ones, remove dropped ones
      const prev = new Set(user?.roles ?? []);
      const roleMap = new Map(roles.map((r) => [r.name, r.id]));

      for (const roleName of selectedRoles) {
        if (!prev.has(roleName)) {
          const rid = roleMap.get(roleName);
          if (rid) await assignRole(savedUser.id, rid);
        }
      }
      for (const roleName of prev) {
        if (!selectedRoles.has(roleName)) {
          const rid = roleMap.get(roleName);
          if (rid) await removeRole(savedUser.id, rid);
        }
      }

      onSaved();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to save user.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            {isCreate ? "New User" : `Edit User — ${user!.username}`}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Username (create only) */}
          {isCreate && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          )}

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Full name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password {isCreate && <span className="text-red-500">*</span>}
              {!isCreate && <span className="ml-1 text-xs text-gray-400">(leave blank to keep current)</span>}
            </label>
            <input
              type="password"
              required={isCreate}
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Active toggle (edit only) */}
          {!isCreate && (
            <div className="flex items-center gap-3">
              <input
                id="is-active"
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="is-active" className="text-sm text-gray-700">Active</label>
            </div>
          )}

          {/* Role assignment */}
          {roles.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Roles</p>
              <div className="rounded-md border border-gray-200 bg-gray-50 p-3 space-y-1.5 max-h-40 overflow-y-auto">
                {roles.map((role) => (
                  <label key={role.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedRoles.has(role.name)}
                      onChange={() => toggleRole(role.name)}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600"
                    />
                    <span className="text-sm text-gray-800">{role.name}</span>
                    {role.description && (
                      <span className="text-xs text-gray-400">— {role.description}</span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          )}

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}

          {/* Footer buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving…" : isCreate ? "Create User" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
