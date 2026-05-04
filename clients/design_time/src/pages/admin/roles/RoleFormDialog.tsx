/**
 * ROLE FORM DIALOG — create a new role, or edit an existing role's description
 * and permission strings (add new ones / remove existing ones).
 *
 * System roles are read-only — editing is disabled for them.
 */

import { useState } from "react";
import { XMarkIcon, TrashIcon, PlusIcon } from "@heroicons/react/24/outline";
import {
  createRole,
  updateRolePermissions,
  type RoleRead,
} from "../../api/auth";

interface Props {
  role: RoleRead | null;  // null = create mode
  onClose: () => void;
  onSaved: () => void;
}

export default function RoleFormDialog({ role, onClose, onSaved }: Props) {
  const isCreate = role === null;

  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");

  // Permissions management (edit mode only)
  const [existingPerms, setExistingPerms] = useState<string[]>(role?.permissions ?? []);
  const [removedPerms, setRemovedPerms] = useState<Set<string>>(new Set());
  const [addedPerms, setAddedPerms] = useState<string[]>([]);
  const [newPerm, setNewPerm] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function handleRemoveExisting(perm: string) {
    setRemovedPerms((prev) => new Set([...prev, perm]));
  }

  function handleAddPerm() {
    const trimmed = newPerm.trim();
    if (!trimmed) return;
    if (existingPerms.includes(trimmed) || addedPerms.includes(trimmed)) return;
    setAddedPerms((prev) => [...prev, trimmed]);
    setNewPerm("");
  }

  function handleRemoveAdded(perm: string) {
    setAddedPerms((prev) => prev.filter((p) => p !== perm));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (isCreate) {
        await createRole({ name, description: description || undefined });
      } else {
        // Update permissions diff
        const toRemove = [...removedPerms];
        if (addedPerms.length > 0 || toRemove.length > 0) {
          await updateRolePermissions(role!.id, addedPerms, toRemove);
        }
      }
      onSaved();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to save role.");
    } finally {
      setSaving(false);
    }
  }

  const isReadOnly = !isCreate && role!.is_system;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            {isCreate ? "New Role" : `${isReadOnly ? "View" : "Edit"} Role — ${role!.name}`}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Name (create only) */}
          {isCreate && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          )}

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              disabled={isReadOnly}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          {/* Permissions (edit mode only) */}
          {!isCreate && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Permissions</p>

              <div className="rounded-md border border-gray-200 bg-gray-50 p-3 max-h-48 overflow-y-auto space-y-1.5">
                {existingPerms.filter((p) => !removedPerms.has(p)).map((perm) => (
                  <div key={perm} className="flex items-center justify-between gap-2 group">
                    <code className="text-xs text-gray-700 font-mono">{perm}</code>
                    {!isReadOnly && (
                      <button
                        type="button"
                        onClick={() => handleRemoveExisting(perm)}
                        className="rounded p-0.5 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Remove permission"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
                {addedPerms.map((perm) => (
                  <div key={perm} className="flex items-center justify-between gap-2 group">
                    <code className="text-xs text-indigo-600 font-mono">{perm}</code>
                    <button
                      type="button"
                      onClick={() => handleRemoveAdded(perm)}
                      className="rounded p-0.5 text-indigo-300 hover:text-red-500"
                      title="Remove"
                    >
                      <TrashIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
                {existingPerms.filter((p) => !removedPerms.has(p)).length === 0 &&
                  addedPerms.length === 0 && (
                    <p className="text-xs text-gray-400 italic">No permissions.</p>
                  )}
              </div>

              {/* Add permission input */}
              {!isReadOnly && (
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. module.resource.action"
                    value={newPerm}
                    onChange={(e) => setNewPerm(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddPerm();
                      }
                    }}
                    className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={handleAddPerm}
                    className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <PlusIcon className="h-3.5 w-3.5" />
                    Add
                  </button>
                </div>
              )}
            </div>
          )}

          {isReadOnly && (
            <p className="rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-700">
              System roles cannot be modified.
            </p>
          )}

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}

          {/* Footer */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {isReadOnly ? "Close" : "Cancel"}
            </button>
            {!isReadOnly && (
              <button
                type="submit"
                disabled={saving}
                className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
              >
                {saving ? "Saving…" : isCreate ? "Create Role" : "Save Changes"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
