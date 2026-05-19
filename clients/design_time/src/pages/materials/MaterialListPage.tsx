/**
 * Material List Page — table of material definitions with type filter and CRUD.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import { useMaterials, useDeleteMaterial } from "../../hooks/useMaterial";
import type { Material } from "../../types";
import MaterialFormDialog from "./MaterialFormDialog";

const MATERIAL_TYPES = ["raw", "intermediate", "finished"];

export default function MaterialListPage() {
  const [editing, setEditing] = useState<Material | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");

  const { data, isLoading, error } = useMaterials();
  const deleteMut = useDeleteMaterial();

  const materials = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!typeFilter) return materials;
    return materials.filter((m) => m.material_type === typeFilter);
  }, [materials, typeFilter]);

  const handleDelete = (m: Material) => {
    if (!confirm(`Delete material "${m.code}"?`)) return;
    deleteMut.mutate(m.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Materials</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define raw, intermediate, and finished material specifications.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Material
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">
          Filter by type:
        </label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All types</option>
          {MATERIAL_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} material{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading materials…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load materials. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  UoM
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Shelf Life (days)
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((m) => (
                <tr
                  key={m.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                    {m.code}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">
                    {m.name}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        m.material_type === "raw"
                          ? "bg-amber-50 text-amber-700"
                          : m.material_type === "intermediate"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-green-50 text-green-700"
                      }`}
                    >
                      {m.material_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm font-mono text-gray-600">
                    {m.uom_symbol}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">
                    {m.shelf_life_days ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(m)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(m)}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No materials found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <MaterialFormDialog
          material={editing}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
