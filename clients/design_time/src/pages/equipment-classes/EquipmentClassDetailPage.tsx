/**
 * Equipment Class Detail Page — manage properties for an equipment class.
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeftIcon,
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  useEquipmentClassDetail,
  useClassProperties,
  useDeleteClassProperty,
} from "../../hooks/usePhysicalModel";
import { useUoMs } from "../../hooks/useUoM";
import type { EquipmentClassProperty } from "../../types";
import ClassPropertyFormDialog from "./ClassPropertyFormDialog";
const DATA_TYPE_BADGE: Record<string, string> = {
  string: "bg-blue-100 text-blue-800",
  float: "bg-green-100 text-green-800",
  int: "bg-purple-100 text-purple-800",
  boolean: "bg-amber-100 text-amber-800",
};

export default function EquipmentClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const { data: classDetail, isLoading: loadingClass } = useEquipmentClassDetail(classId ?? "");
  const { data: properties, isLoading: loadingProps } = useClassProperties(classId ?? "");
  const { data: uomResp } = useUoMs();
  const deleteMut = useDeleteClassProperty();

  const uomSymbolById = new Map<string, string>(
    (uomResp?.data ?? []).map((u) => [u.id, u.symbol]),
  );

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<EquipmentClassProperty | null>(null);

  const props = properties ?? classDetail?.properties ?? [];

  function handleEdit(prop: EquipmentClassProperty) {
    setEditing(prop);
    setFormOpen(true);
  }

  function handleDelete(prop: EquipmentClassProperty) {
    if (!confirm(`Delete property "${prop.name}"?`)) return;
    deleteMut.mutate(prop.id);
  }

  if (loadingClass || loadingProps) return <p className="p-6 text-gray-500">Loading…</p>;
  if (!classDetail) return <p className="p-6 text-red-600">Equipment class not found.</p>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Back + header */}
      <button
        onClick={() => navigate("/equipment-classes")}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeftIcon className="h-4 w-4" /> Back to Equipment Classes
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{classDetail.name}</h1>
          <p className="text-sm text-gray-500 mt-1">
            Code: <span className="font-mono">{classDetail.code}</span>
            {classDetail.description && <> — {classDetail.description}</>}
            <span className="ml-3 text-gray-400">({classDetail.member_count} equipment assigned)</span>
          </p>
        </div>
        <button
          onClick={() => { setEditing(null); setFormOpen(true); }}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <PlusIcon className="h-4 w-4" /> Add Property
        </button>
      </div>

      {/* Members (assigned equipment) */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Assigned Equipment
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({classDetail.members?.length ?? 0})
          </span>
        </h2>
        {!classDetail.members || classDetail.members.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-4">
            No equipment has been assigned to this class yet.
          </p>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 border rounded-lg overflow-x-auto">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Code</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">State Model</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Queue Depth</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {classDetail.members.map((eq) => (
                <tr key={eq.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono font-medium text-gray-900">{eq.code}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{eq.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 font-mono">{eq.state_model_id ?? "—"}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{eq.max_queue_depth ?? "—"}</td>
                  <td className="px-4 py-3 text-sm">
                    {eq.is_active ? (
                      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">active</span>
                    ) : (
                      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">inactive</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <h2 className="text-lg font-semibold text-gray-900 mb-2">Class Properties</h2>

      {/* Properties table */}
      {props.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p>No properties defined for this class.</p>
          <p className="text-sm mt-1">Properties define measurable attributes like speed, temperature, etc.</p>
        </div>
      ) : (
        <table className="min-w-full divide-y divide-gray-200 border rounded-lg overflow-x-auto">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Data Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">UoM</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Default</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Description</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {props.map((prop) => (
              <tr key={prop.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{prop.name}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${DATA_TYPE_BADGE[prop.data_type] ?? "bg-gray-100 text-gray-700"}`}>
                    {prop.data_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600 font-mono">
                  {prop.uom_id ? uomSymbolById.get(prop.uom_id) ?? prop.uom_id : "—"}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">{prop.default_value ?? "—"}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{prop.description ?? "—"}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => handleEdit(prop)}
                      title="Edit"
                      className="p-1.5 rounded hover:bg-gray-200 text-gray-600"
                    >
                      <PencilSquareIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(prop)}
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
        <ClassPropertyFormDialog
          classId={classId!}
          existing={editing}
          onClose={() => { setFormOpen(false); setEditing(null); }}
        />
      )}
    </div>
  );
}
