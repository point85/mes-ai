/**
 * Equipment Class List Page — CRUD for ISA-95 Equipment Classes.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  WrenchScrewdriverIcon,
} from "@heroicons/react/24/outline";
import {
  useEquipmentClasses,
  useDeleteEquipmentClass,
} from "../../hooks/usePhysicalModel";
import type { EquipmentClass } from "../../types";
import EquipmentClassFormDialog from "./EquipmentClassFormDialog";

export default function EquipmentClassListPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useEquipmentClasses();
  const deleteMut = useDeleteEquipmentClass();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<EquipmentClass | null>(null);

  const classes = data?.data ?? [];

  function handleEdit(ec: EquipmentClass) {
    setEditing(ec);
    setFormOpen(true);
  }

  function handleDelete(ec: EquipmentClass) {
    if (!confirm(`Delete equipment class "${ec.name}"?`)) return;
    deleteMut.mutate(ec.id);
  }

  if (isLoading) return <p className="p-6 text-gray-500">Loading…</p>;
  if (error) return <p className="p-6 text-red-600">Error loading equipment classes.</p>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Equipment Classes</h1>
          <p className="text-sm text-gray-500 mt-1">ISA-95 Part 2 equipment classifications</p>
        </div>
        <button
          onClick={() => { setEditing(null); setFormOpen(true); }}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <PlusIcon className="h-4 w-4" /> New Class
        </button>
      </div>

      {/* Table */}
      {classes.length === 0 ? (
        <p className="text-gray-500">No equipment classes defined. Create one to get started.</p>
      ) : (
        <table className="min-w-full divide-y divide-gray-200 border rounded-lg overflow-x-auto">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Code</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Description</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {classes.map((ec) => (
              <tr key={ec.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{ec.name}</td>
                <td className="px-4 py-3 text-sm text-gray-600 font-mono">{ec.code}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{ec.description ?? "—"}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => navigate(`/equipment-classes/${ec.id}`)}
                      title="Properties"
                      className="p-1.5 rounded hover:bg-indigo-100 text-indigo-600"
                    >
                      <WrenchScrewdriverIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleEdit(ec)}
                      title="Edit"
                      className="p-1.5 rounded hover:bg-gray-200 text-gray-600"
                    >
                      <PencilSquareIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(ec)}
                      title="Delete"
                      className="p-1.5 rounded hover:bg-red-100 text-red-600"
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

      {/* Form dialog */}
      {formOpen && (
        <EquipmentClassFormDialog
          existing={editing}
          onClose={() => { setFormOpen(false); setEditing(null); }}
        />
      )}
    </div>
  );
}
