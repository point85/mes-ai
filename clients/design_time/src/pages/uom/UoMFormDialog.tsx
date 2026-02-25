/**
 * UoM Create / Edit dialog — modal form with Zod validation.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateUoM, useUpdateUoM } from "../../hooks/useUoM";
import type { UoM } from "../../types";

const uomSchema = z.object({
  symbol: z
    .string()
    .min(1, "Symbol is required")
    .max(20)
    .refine((s) => !s.includes(" "), "Symbol must not contain spaces"),
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().nullable().optional(),
  uom_type: z.string().min(1, "Type is required").max(50),
  multiplier: z.coerce.number().positive("Must be > 0"),
  offset: z.coerce.number(),
});

type UoMFormData = z.infer<typeof uomSchema>;

interface Props {
  uom: UoM | null; // null = create mode
  onClose: () => void;
}

export default function UoMFormDialog({ uom, onClose }: Props) {
  const isEdit = !!uom;
  const createMut = useCreateUoM();
  const updateMut = useUpdateUoM();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<UoMFormData>({
    resolver: zodResolver(uomSchema),
    defaultValues: {
      symbol: "",
      name: "",
      description: "",
      uom_type: "",
      multiplier: 1,
      offset: 0,
    },
  });

  useEffect(() => {
    if (uom) {
      reset({
        symbol: uom.symbol,
        name: uom.name,
        description: uom.description ?? "",
        uom_type: uom.uom_type,
        multiplier: uom.multiplier,
        offset: uom.offset,
      });
    }
  }, [uom, reset]);

  const onSubmit = async (data: UoMFormData) => {
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: uom!.id, ...data });
      } else {
        await createMut.mutateAsync(data);
      }
      onClose();
    } catch {
      // Error is shown by TanStack Query / mutation state
    }
  };

  const mutError = createMut.error || updateMut.error;

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

      {/* Panel */}
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Unit" : "New Unit of Measure"}
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
              {(mutError as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                "An error occurred"}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Symbol */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Symbol
              </label>
              <input
                {...register("symbol")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="kg, lb, case, …"
              />
              {errors.symbol && (
                <p className="mt-1 text-xs text-red-600">{errors.symbol.message}</p>
              )}
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                {...register("name")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="kilogram, pound, case, …"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
              )}
            </div>

            {/* Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Type
              </label>
              <input
                {...register("uom_type")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="mass, time, length, count, …"
              />
              {errors.uom_type && (
                <p className="mt-1 text-xs text-red-600">{errors.uom_type.message}</p>
              )}
            </div>

            {/* Multiplier + Offset side-by-side */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Multiplier
                </label>
                <input
                  type="number"
                  step="any"
                  {...register("multiplier")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.multiplier && (
                  <p className="mt-1 text-xs text-red-600">{errors.multiplier.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Offset
                </label>
                <input
                  type="number"
                  step="any"
                  {...register("offset")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.offset && (
                  <p className="mt-1 text-xs text-red-600">{errors.offset.message}</p>
                )}
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                {...register("description")}
                rows={2}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
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
