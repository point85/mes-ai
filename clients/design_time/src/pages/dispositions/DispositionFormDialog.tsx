/**
 * Disposition Form Dialog — create/edit a disposition in a modal dialog.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateDisposition, useUpdateDisposition } from "../../hooks/useProductDef";
import type { Disposition, DispositionCreate } from "../../types";

const CATEGORIES = [
  { value: "route", label: "Route" },
  { value: "hold", label: "Hold" },
  { value: "scrap", label: "Scrap" },
];

interface Props {
  disposition: Disposition | null; // null = create mode
  onClose: () => void;
}

export default function DispositionFormDialog({ disposition, onClose }: Props) {
  const createMut = useCreateDisposition();
  const updateMut = useUpdateDisposition();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DispositionCreate>({
    defaultValues: {
      code: disposition?.code ?? "",
      name: disposition?.name ?? "",
      description: disposition?.description ?? "",
      category: disposition?.category ?? "route",
    },
  });

  useEffect(() => {
    reset({
      code: disposition?.code ?? "",
      name: disposition?.name ?? "",
      description: disposition?.description ?? "",
      category: disposition?.category ?? "route",
    });
  }, [disposition, reset]);

  const onSubmit = async (data: DispositionCreate) => {
    const payload = {
      ...data,
      description: data.description || null,
    };
    if (disposition) {
      const { code: _code, ...updateData } = payload;
      await updateMut.mutateAsync({ id: disposition.id, ...updateData });
    } else {
      await createMut.mutateAsync(payload);
    }
    onClose();
  };

  const mutError = createMut.error || updateMut.error;

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {disposition ? "Edit Disposition" : "New Disposition"}
            </DialogTitle>
            <button onClick={onClose} className="rounded p-1 text-gray-400 hover:text-gray-600">
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
            {/* Code (only on create) */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Code</label>
              <input
                {...register("code", { required: "Code is required" })}
                disabled={!!disposition}
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

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Category</label>
              <select
                {...register("category")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Actions */}
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
                {isSubmitting ? "Saving…" : disposition ? "Save" : "Create"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
