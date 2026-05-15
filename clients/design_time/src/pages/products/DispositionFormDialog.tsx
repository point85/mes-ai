/**
 * Disposition Create / Edit dialog — creates or edits a disposition on a step.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateDisposition,
  useUpdateDisposition,
} from "../../hooks/useProductDef";
import type { Disposition } from "../../types";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).nullable().optional(),
  category: z.enum(["route", "hold", "scrap", "release"]),
});

type FormData = z.infer<typeof schema>;

interface Props {
  stepId: string;
  disposition: Disposition | null;
  onClose: () => void;
}

export default function DispositionFormDialog({
  stepId,
  disposition,
  onClose,
}: Props) {
  const isEdit = !!disposition;
  const createMut = useCreateDisposition();
  const updateMut = useUpdateDisposition();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      name: "",
      description: "",
      category: "route",
    },
  });

  useEffect(() => {
    if (disposition) {
      reset({
        name: disposition.name,
        description: disposition.description ?? "",
        category: disposition.category as FormData["category"],
      });
    }
  }, [disposition, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: disposition!.id, ...data });
      } else {
        await createMut.mutateAsync({ stepId, ...data });
      }
      onClose();
    } catch {
      // error shown via mutation state
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
              {isEdit ? "Edit Disposition" : "New Disposition"}
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
              {(mutError as Error).message || "Save failed"}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                {...register("name")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. AOI Pass"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                {...register("description")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Optional description"
              />
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                {...register("category")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="route">Route</option>
                <option value="hold">Hold</option>
                <option value="scrap">Scrap</option>
                <option value="release">Release</option>
              </select>
              {errors.category && (
                <p className="mt-1 text-xs text-red-600">{errors.category.message}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
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
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                {isEdit ? "Save" : "Create"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
