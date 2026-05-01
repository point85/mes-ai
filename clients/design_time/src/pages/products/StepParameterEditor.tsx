/**
 * Step Parameter sub-editor — manages SegmentParameter specs for a
 * ProcessSegment (ISA-95 Part 2). Each parameter captures a data-collection
 * or process-spec datum expected at the step (name, data type, optional UoM,
 * target value, lower/upper limits, required flag).
 */

import { useState } from "react";
import { TrashIcon, PlusIcon, PencilSquareIcon, CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";
import {
  useStepParameters,
  useCreateStepParameter,
  useUpdateStepParameter,
  useDeleteStepParameter,
} from "../../hooks/useProductDef";
import { useUoMs } from "../../hooks/useUoM";
import type { StepParameter } from "../../types";

interface Props {
  stepId: string;
}

const DATA_TYPES = ["numeric", "string", "boolean", "enum"] as const;
type DataType = (typeof DATA_TYPES)[number];

interface FormState {
  name: string;
  data_type: DataType;
  uom_id: string;
  target_value: string;
  lower_limit: string;
  upper_limit: string;
  is_required: boolean;
}

const EMPTY_FORM: FormState = {
  name: "",
  data_type: "numeric",
  uom_id: "",
  target_value: "",
  lower_limit: "",
  upper_limit: "",
  is_required: false,
};

export default function StepParameterEditor({ stepId }: Props) {
  const { data: paramsResp, isLoading } = useStepParameters(stepId);
  const params = (paramsResp?.data ?? [])
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name));
  const createMut = useCreateStepParameter();
  const updateMut = useUpdateStepParameter();
  const deleteMut = useDeleteStepParameter();

  const { data: uomData } = useUoMs();
  const nonRateUoMs = (uomData?.data ?? []).filter((u) => u.uom_type !== "rate");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setFormError(null);
  };

  const beginEdit = (p: StepParameter) => {
    setEditingId(p.id);
    setForm({
      name: p.name,
      data_type: (DATA_TYPES as readonly string[]).includes(p.data_type)
        ? (p.data_type as DataType)
        : "numeric",
      uom_id: p.uom_id ?? "",
      target_value: p.target_value ?? "",
      lower_limit: p.lower_limit ?? "",
      upper_limit: p.upper_limit ?? "",
      is_required: p.is_required,
    });
    setFormError(null);
  };

  const handleSubmit = async () => {
    setFormError(null);
    if (!form.name.trim()) {
      setFormError("Name is required.");
      return;
    }
    const payload = {
      name: form.name.trim(),
      data_type: form.data_type,
      uom_id: form.uom_id.trim() || null,
      target_value: form.target_value.trim() || null,
      lower_limit: form.lower_limit.trim() || null,
      upper_limit: form.upper_limit.trim() || null,
      is_required: form.is_required,
    };
    try {
      if (editingId) {
        await updateMut.mutateAsync({ id: editingId, ...payload });
      } else {
        await createMut.mutateAsync({ stepId, ...payload });
      }
      resetForm();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setFormError(detail ?? "Failed to save parameter.");
    }
  };

  const dataTypeBadge = (dt: string) => {
    const styles: Record<string, string> = {
      numeric: "bg-blue-100 text-blue-800",
      string: "bg-gray-100 text-gray-700",
      boolean: "bg-green-100 text-green-800",
      enum: "bg-purple-100 text-purple-800",
    };
    return (
      <span
        className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
          styles[dt] ?? "bg-gray-100 text-gray-700"
        }`}
      >
        {dt}
      </span>
    );
  };

  const rangeLabel = (p: StepParameter): string => {
    const parts: string[] = [];
    if (p.target_value) parts.push(`target=${p.target_value}`);
    if (p.lower_limit || p.upper_limit) {
      parts.push(`[${p.lower_limit ?? "−∞"}, ${p.upper_limit ?? "+∞"}]`);
    }
    if (p.uom_symbol) parts.push(p.uom_symbol);
    return parts.join(" ");
  };

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-800">
            Step Parameters
          </h4>
          <p className="text-xs text-gray-500">
            Data-collection specs (measurements, set-points, attributes)
            captured at this step.
          </p>
        </div>
      </div>

      {isLoading ? (
        <p className="text-xs text-gray-500">Loading…</p>
      ) : params.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 bg-white px-3 py-2 text-xs text-gray-500">
          No parameters defined. Add one below.
        </p>
      ) : (
        <ul className="space-y-1">
          {params.map((p) => (
            <li
              key={p.id}
              className="flex items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5 text-xs"
            >
              <span className="flex-1 truncate">
                <span className="font-medium text-gray-900">{p.name}</span>
                {rangeLabel(p) && (
                  <span className="ml-2 text-gray-500">{rangeLabel(p)}</span>
                )}
              </span>
              {dataTypeBadge(p.data_type)}
              {p.is_required && (
                <span className="inline-block rounded bg-red-50 px-1.5 py-0.5 text-xs font-medium text-red-700">
                  required
                </span>
              )}
              <button
                type="button"
                onClick={() => beginEdit(p)}
                className="rounded p-1 text-gray-400 hover:text-indigo-600"
                aria-label="Edit parameter"
              >
                <PencilSquareIcon className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`Delete parameter "${p.name}"?`)) {
                    deleteMut.mutate(p.id);
                  }
                }}
                className="rounded p-1 text-gray-400 hover:text-red-600"
                aria-label="Remove parameter"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Add / Edit form */}
      <div className="mt-3 rounded border border-gray-200 bg-white p-2">
        <div className="mb-2 text-xs font-semibold text-gray-700">
          {editingId ? "Edit parameter" : "Add parameter"}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="col-span-2 sm:col-span-1">
            <label className="block text-xs text-gray-500">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Torque, Temperature, Serial #, …"
              className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-xs"
            />
          </div>
          <div className="col-span-2 sm:col-span-1">
            <label className="block text-xs text-gray-500">Data type</label>
            <select
              value={form.data_type}
              onChange={(e) =>
                setForm({ ...form, data_type: e.target.value as DataType })
              }
              className="mt-0.5 block w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs"
            >
              {DATA_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500">UoM</label>
            <select
              value={form.uom_id}
              onChange={(e) => setForm({ ...form, uom_id: e.target.value })}
              className="mt-0.5 block w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs"
              disabled={form.data_type !== "numeric"}
            >
              <option value="">— none —</option>
              {nonRateUoMs.map((u) => (
                <option key={u.id} value={u.id}>{u.symbol} — {u.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500">Target</label>
            <input
              type="text"
              value={form.target_value}
              onChange={(e) =>
                setForm({ ...form, target_value: e.target.value })
              }
              placeholder="setpoint"
              className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500">Lower limit</label>
            <input
              type="text"
              value={form.lower_limit}
              onChange={(e) =>
                setForm({ ...form, lower_limit: e.target.value })
              }
              className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-xs"
              disabled={form.data_type !== "numeric"}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500">Upper limit</label>
            <input
              type="text"
              value={form.upper_limit}
              onChange={(e) =>
                setForm({ ...form, upper_limit: e.target.value })
              }
              className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-xs"
              disabled={form.data_type !== "numeric"}
            />
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <label className="inline-flex items-center gap-1.5 text-xs text-gray-700">
            <input
              type="checkbox"
              checked={form.is_required}
              onChange={(e) =>
                setForm({ ...form, is_required: e.target.checked })
              }
              className="h-3.5 w-3.5 rounded border-gray-300"
            />
            Required
          </label>
          <div className="flex items-center gap-1">
            {editingId && (
              <button
                type="button"
                onClick={resetForm}
                className="inline-flex items-center gap-1 rounded border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                <XMarkIcon className="h-3.5 w-3.5" />
                Cancel
              </button>
            )}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={
                createMut.isPending || updateMut.isPending || !form.name.trim()
              }
              className="inline-flex items-center gap-1 rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {editingId ? (
                <>
                  <CheckIcon className="h-3.5 w-3.5" />
                  Save
                </>
              ) : (
                <>
                  <PlusIcon className="h-3.5 w-3.5" />
                  Add
                </>
              )}
            </button>
          </div>
        </div>
        {formError && <p className="mt-1 text-xs text-red-600">{formError}</p>}
      </div>
    </div>
  );
}
