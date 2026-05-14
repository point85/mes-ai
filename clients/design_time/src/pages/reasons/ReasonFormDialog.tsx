/**
 * Reason Form Dialog — create/edit a reason in a modal dialog.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useCreateReason, useUpdateReason, useReasons } from "../../hooks/usePerformance";
import type { Reason, ReasonCreate } from "../../types";

const OEE_BUCKETS = [
  { value: "downtime_unplanned", label: "Downtime — Unplanned" },
  { value: "downtime_planned", label: "Downtime — Planned" },
  { value: "uptime_non_value", label: "Uptime — Non-Value Add" },
  { value: "uptime_value_add", label: "Uptime — Value Add" },
  { value: "excluded", label: "Excluded" },
];

interface Props {
  reason: Reason | null; // null = create mode
  parentId?: string | null;
  onClose: () => void;
}

export default function ReasonFormDialog({ reason, parentId, onClose }: Props) {
  const createMut = useCreateReason();
  const updateMut = useUpdateReason();
  const { data: allReasons } = useReasons();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ReasonCreate>({
    defaultValues: {
      code: reason?.code ?? "",
      name: reason?.name ?? "",
      description: reason?.description ?? "",
      oee_bucket: reason?.oee_bucket ?? "downtime_unplanned",
      parent_id: reason?.parent_id ?? parentId ?? undefined,
    },
  });

  useEffect(() => {
    reset({
      code: reason?.code ?? "",
      name: reason?.name ?? "",
      description: reason?.description ?? "",
      oee_bucket: reason?.oee_bucket ?? "downtime_unplanned",
      parent_id: reason?.parent_id ?? parentId ?? undefined,
    });
  }, [reason, parentId, reset]);

  const onSubmit = async (data: ReasonCreate) => {
    const payload = {
      ...data,
      parent_id: data.parent_id || null,
      description: data.description || null,
    };
    if (reason) {
      const { code: _code, ...updateData } = payload;
      await updateMut.mutateAsync({ id: reason.id, ...updateData });
    } else {
      await createMut.mutateAsync(payload);
    }
    onClose();
  };

  // Build flat list of potential parents (excluding self and descendants)
  const parentOptions = (allReasons ?? []).filter(
    (r) => !reason || r.id !== reason.id,
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">
          {reason ? "Edit Reason" : "New Reason"}
        </h2>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4">
          {/* Code (only on create) */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Code (up to 4 characters)
            </label>
            <input
              {...register("code", {
                required: "Code is required",
                maxLength: { value: 4, message: "Code must be 4 characters or fewer" },
              })}
              disabled={!!reason}
              maxLength={4}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100"
            />
            {errors.code && (
              <p className="mt-1 text-xs text-red-600">{errors.code.message}</p>
            )}
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              {...register("name", { required: "Name is required" })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
            {errors.name && (
              <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              {...register("description")}
              rows={2}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* OEE Bucket */}
          <div>
            <label className="block text-sm font-medium text-gray-700">OEE Loss Bucket</label>
            <select
              {...register("oee_bucket", { required: "OEE bucket is required" })}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              {OEE_BUCKETS.map((b) => (
                <option key={b.value} value={b.value}>
                  {b.label}
                </option>
              ))}
            </select>
          </div>

          {/* Parent */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Parent Reason</label>
            <select
              {...register("parent_id")}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">— Top Level —</option>
              {parentOptions.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.code} {r.name}
                </option>
              ))}
            </select>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              {reason ? "Save" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
