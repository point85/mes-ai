/**
 * Equipment Capabilities Page — ISA-95 Part 2 capability declarations
 * for a specific piece of equipment. Shows formal typed capabilities
 * with property values derived from the equipment class definition.
 */

import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PlusIcon, TrashIcon, PencilSquareIcon, ArrowLeftIcon } from "@heroicons/react/24/outline";
import {
  useEquipmentCapabilities,
  useEquipmentClasses,
  useEquipmentClassDetail,
  useCreateEquipmentCapability,
  useUpdateEquipmentCapability,
  useDeleteEquipmentCapability,
} from "../../hooks/usePhysicalModel";
import type {
  EquipmentCapabilityRead,
  EquipmentCapabilityPropertyCreate,
  EquipmentClassProperty,
} from "../../types";

export default function EquipmentCapabilityPage() {
  const { equipId } = useParams<{ equipId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useEquipmentCapabilities(equipId!);
  const { data: classesResp } = useEquipmentClasses();
  const createMut = useCreateEquipmentCapability();
  const updateMut = useUpdateEquipmentCapability();
  const deleteMut = useDeleteEquipmentCapability();

  const capabilities: EquipmentCapabilityRead[] = data?.data ?? [];
  const equipmentClasses = classesResp?.data ?? [];

  // ─── New/Edit capability form state ───────────────────────────────
  const [showForm, setShowForm] = useState(false);
  const [editingCap, setEditingCap] = useState<EquipmentCapabilityRead | null>(null);
  const [formClassId, setFormClassId] = useState("");
  const [formType, setFormType] = useState("available");
  const [formReason, setFormReason] = useState("");
  const [formPropertyValues, setFormPropertyValues] = useState<Record<string, string>>({});

  // Load class detail when a class is selected in the form
  const { data: classDetail } = useEquipmentClassDetail(formClassId);
  const classProperties: EquipmentClassProperty[] = classDetail?.properties ?? [];

  // Build class name lookup
  const classMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of equipmentClasses) {
      map.set(c.id, `${c.name} (${c.code})`);
    }
    return map;
  }, [equipmentClasses]);

  const handleClassChange = (classId: string) => {
    setFormClassId(classId);
    setFormPropertyValues({});
  };

  const resetForm = () => {
    setShowForm(false);
    setEditingCap(null);
    setFormClassId("");
    setFormType("available");
    setFormReason("");
    setFormPropertyValues({});
  };

  const handleEdit = (cap: EquipmentCapabilityRead) => {
    setEditingCap(cap);
    setFormClassId(cap.equipment_class_id ?? "");
    setFormType(cap.capability_type);
    setFormReason(cap.reason ?? "");
    setFormPropertyValues({});
    setShowForm(true);
  };

  const handleSave = async () => {
    if (editingCap) {
      await updateMut.mutateAsync({
        id: editingCap.id,
        equipment_class_id: formClassId || null,
        capability_type: formType,
        reason: formReason || null,
      });
      resetForm();
      return;
    }

    const properties: EquipmentCapabilityPropertyCreate[] = [];
    for (const prop of classProperties) {
      const val = formPropertyValues[prop.id];
      if (val?.trim()) {
        properties.push({ class_property_id: prop.id, value: val.trim() });
      }
    }

    await createMut.mutateAsync({
      equipId: equipId!,
      equipment_class_id: formClassId || undefined,
      capability_type: formType,
      reason: formReason || undefined,
      properties,
    });

    resetForm();
  };

  const handleDelete = async (capId: string) => {
    if (!confirm("Delete this capability?")) return;
    await deleteMut.mutateAsync(capId);
  };

  return (
    <div className="space-y-6">
      {/* Back link */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-500"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Equipment
      </button>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Equipment Capabilities</h1>
          <p className="text-sm text-gray-500 mt-1">
            ISA-95 Part 2 formal capability declarations.
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          Add Capability
        </button>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading capabilities…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load capabilities.
        </div>
      )}

      {/* Create/edit form */}
      {showForm && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">
            {editingCap ? "Edit Capability" : "New Capability"}
          </h3>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700">Equipment Class</label>
              <select
                value={formClassId}
                onChange={(e) => handleClassChange(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">None</option>
                {equipmentClasses.map((ec) => (
                  <option key={ec.id} value={ec.id}>
                    {ec.name} ({ec.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">Capability Type</label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="available">Available</option>
                <option value="committed">Committed</option>
                <option value="unattainable">Unattainable</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">
                Reason <span className="text-gray-400">(optional)</span>
              </label>
              <input
                value={formReason}
                onChange={(e) => setFormReason(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g. Scheduled maintenance"
              />
            </div>
          </div>

          {/* Class property values — create mode only (server update schema excludes properties) */}
          {!editingCap && classProperties.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-700 mb-2">Property Values</h4>
              <div className="grid grid-cols-2 gap-3">
                {classProperties.map((prop) => (
                  <div key={prop.id}>
                    <label className="block text-xs text-gray-600">
                      {prop.name}
                      <span className="text-gray-400 ml-1">
                        ({prop.data_type}{prop.uom_id ? `, ${prop.uom_id}` : ""})
                      </span>
                    </label>
                    <input
                      value={formPropertyValues[prop.id] ?? prop.default_value ?? ""}
                      onChange={(e) =>
                        setFormPropertyValues((prev) => ({ ...prev, [prop.id]: e.target.value }))
                      }
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                      placeholder={prop.default_value ?? ""}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {(createMut.error || updateMut.error) && (
            <p className="text-xs text-red-600">
              {((editingCap ? updateMut.error : createMut.error) as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail ?? "Failed to save capability"}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={resetForm}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={createMut.isPending || updateMut.isPending}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {editingCap
                ? updateMut.isPending
                  ? "Saving…"
                  : "Save"
                : createMut.isPending
                  ? "Creating…"
                  : "Create"}
            </button>
          </div>
        </div>
      )}

      {/* Capability cards */}
      {!isLoading && !error && capabilities.length === 0 && !showForm && (
        <p className="text-sm text-gray-400 text-center py-8">
          No capabilities declared. Click "Add Capability" to define one.
        </p>
      )}

      <div className="space-y-4">
        {capabilities.map((cap) => (
          <div
            key={cap.id}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      cap.capability_type === "available"
                        ? "bg-green-100 text-green-700"
                        : cap.capability_type === "committed"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-red-100 text-red-700"
                    }`}
                  >
                    {cap.capability_type}
                  </span>
                  {cap.equipment_class_id && (
                    <span className="text-sm text-gray-600">
                      {classMap.get(cap.equipment_class_id) ?? cap.equipment_class_id}
                    </span>
                  )}
                </div>
                {cap.reason && (
                  <p className="text-xs text-gray-500">Reason: {cap.reason}</p>
                )}
                {(cap.start_time || cap.end_time) && (
                  <p className="text-xs text-gray-400">
                    {cap.start_time && `From: ${new Date(cap.start_time).toLocaleString()}`}
                    {cap.start_time && cap.end_time && " — "}
                    {cap.end_time && `Until: ${new Date(cap.end_time).toLocaleString()}`}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleEdit(cap)}
                  className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                  title="Edit"
                >
                  <PencilSquareIcon className="h-4 w-4" />
                </button>
                <button
                  onClick={() => handleDelete(cap.id)}
                  className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                  title="Delete"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Property values */}
            {cap.properties.length > 0 && (
              <div className="mt-3 border-t border-gray-100 pt-3">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="text-gray-500">
                      <th className="text-left font-medium pr-4">Property</th>
                      <th className="text-left font-medium">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {cap.properties.map((p) => (
                      <tr key={p.id}>
                        <td className="py-1 pr-4 text-gray-700 font-mono">
                          {p.property_name ?? p.class_property_id}
                        </td>
                        <td className="py-1 text-gray-900">{p.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
