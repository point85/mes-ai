/**
 * Non-Conformance Create / Edit dialog — modal form with Zod validation.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateNonConformance,
  useUpdateNonConformance,
} from "../../hooks/useQuality";
import type { NonConformance } from "../../types";

const ncSchema = z.object({
  nc_type: z.enum(["defect", "out_of_spec", "other"]),
  description: z.string().min(1, "Description is required"),
  unit_id: z.string().nullable().optional(),
  lot_id: z.string().nullable().optional(),
  step_id: z.string().nullable().optional(),
});

type NCFormData = z.infer<typeof ncSchema>;

interface Props {
  nc: NonConformance | null;
  onClose: () => void;
}

export default function NCFormDialog({ nc, onClose }: Props) {
  const isEdit = !!nc;
  const createMut = useCreateNonConformance();
  const updateMut = useUpdateNonConformance();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<NCFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(ncSchema) as any,
    defaultValues: {
      nc_type: "defect",
      description: "",
      unit_id: "",
      lot_id: "",
      step_id: "",
    },
  });

  useEffect(() => {
    if (nc) {
      reset({
        nc_type: nc.nc_type as "defect" | "out_of_spec" | "other",
        description: nc.description,
        unit_id: nc.unit_id ?? "",
        lot_id: nc.lot_id ?? "",
        step_id: nc.step_id ?? "",
      });
    }
  }, [nc, reset]);

  const onSubmit = async (data: NCFormData) => {
    try {
      const payload = {
        ...data,
        unit_id: data.unit_id || null,
        lot_id: data.lot_id || null,
        step_id: data.step_id || null,
      };
      if (isEdit) {
        await updateMut.mutateAsync({
          id: nc!.id,
          description: payload.description,
        });
      } else {
        await createMut.mutateAsync(payload);
      }
      onClose();
    } catch {
      // Error shown by mutation state
    }
  };

  const mutError = createMut.error || updateMut.error;

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Non-Conformance" : "New Non-Conformance"}
            </DialogTitle>
            <button
              onClick={onClose}
              className="rounded p-1 text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {mutError && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
              {(mutError as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail ?? "An error occurred"}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Type
              </label>
              <select
                {...register("nc_type")}
                disabled={isEdit}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100"
              >
                <option value="defect">Defect</option>
                <option value="out_of_spec">Out of Spec</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                {...register("description")}
                rows={3}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="Describe the non-conformance…"
              />
              {errors.description && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.description.message}
                </p>
              )}
            </div>

            {!isEdit && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Unit ID{" "}
                      <span className="text-gray-400">(opt)</span>
                    </label>
                    <input
                      {...register("unit_id")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      placeholder="UUID"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Lot ID{" "}
                      <span className="text-gray-400">(opt)</span>
                    </label>
                    <input
                      {...register("lot_id")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      placeholder="UUID"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Step ID{" "}
                    <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    {...register("step_id")}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    placeholder="UUID"
                  />
                </div>
              </>
            )}

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
                {isSubmitting ? "Saving…" : isEdit ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
