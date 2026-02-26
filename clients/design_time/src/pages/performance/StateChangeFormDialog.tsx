/**
 * Equipment State Log Create dialog — modal form with Zod validation.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useRecordStateChange } from "../../hooks/usePerformance";

const DISPATCH_CATS = [
  "available",
  "busy",
  "unavailable_planned",
  "unavailable_unplanned",
] as const;

const OEE_BUCKETS = [
  "uptime_value_add",
  "uptime_non_value",
  "downtime_planned",
  "downtime_unplanned",
  "excluded",
] as const;

const stateSchema = z.object({
  equipment_id: z.string().min(1, "Equipment ID is required"),
  state_model: z.string().min(1).max(50),
  state: z.string().min(1, "State is required").max(50),
  sub_state: z.string().nullable().optional(),
  dispatch_category: z.enum(DISPATCH_CATS),
  oee_bucket: z.enum(OEE_BUCKETS),
  started_at: z.string().min(1, "Start time is required"),
  reason_code: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
});

type StateFormData = z.infer<typeof stateSchema>;

interface Props {
  onClose: () => void;
}

export default function StateChangeFormDialog({ onClose }: Props) {
  const mut = useRecordStateChange();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<StateFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(stateSchema) as any,
    defaultValues: {
      equipment_id: "",
      state_model: "default",
      state: "",
      sub_state: "",
      dispatch_category: "available",
      oee_bucket: "uptime_value_add",
      started_at: new Date().toISOString().slice(0, 16),
      reason_code: "",
      notes: "",
    },
  });

  const onSubmit = async (data: StateFormData) => {
    try {
      await mut.mutateAsync({
        ...data,
        sub_state: data.sub_state || undefined,
        reason_code: data.reason_code || undefined,
        notes: data.notes || undefined,
        started_at: new Date(data.started_at).toISOString(),
      });
      onClose();
    } catch {
      // Error shown by mutation state
    }
  };

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              Record State Change
            </DialogTitle>
            <button
              onClick={onClose}
              className="rounded p-1 text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {mut.error && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
              {(mut.error as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail ?? "An error occurred"}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Equipment ID
              </label>
              <input
                {...register("equipment_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="UUID of the equipment"
              />
              {errors.equipment_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.equipment_id.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  State Model
                </label>
                <input
                  {...register("state_model")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  State
                </label>
                <input
                  {...register("state")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="running"
                />
                {errors.state && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.state.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Sub-state{" "}
                  <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  {...register("sub_state")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Dispatch Category
                </label>
                <select
                  {...register("dispatch_category")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {DISPATCH_CATS.map((c) => (
                    <option key={c} value={c}>
                      {c.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  OEE Bucket
                </label>
                <select
                  {...register("oee_bucket")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {OEE_BUCKETS.map((b) => (
                    <option key={b} value={b}>
                      {b.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Started At
                </label>
                <input
                  type="datetime-local"
                  {...register("started_at")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.started_at && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.started_at.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Reason Code{" "}
                  <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  {...register("reason_code")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Notes <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                {...register("notes")}
                rows={2}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
              >
                {isSubmitting ? "Recording…" : "Record"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
