/**
 * BOM Create / Edit dialog — manages a BillOfMaterial header for a product.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateBOM, useUpdateBOM } from "../../hooks/useProductDef";
import type { BOM } from "../../types";

const schema = z.object({
  version: z.string().min(1, "Version is required").max(50),
  effective_date: z.string().nullable().optional(),
  expiry_date: z.string().nullable().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  productId: string;
  bom: BOM | null;
  onClose: () => void;
}

export default function BOMFormDialog({ productId, bom, onClose }: Props) {
  const isEdit = !!bom;
  const createMut = useCreateBOM();
  const updateMut = useUpdateBOM();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { version: "1.0", effective_date: "", expiry_date: "" },
  });

  useEffect(() => {
    if (bom) {
      reset({
        version: bom.version,
        effective_date: bom.effective_date ?? "",
        expiry_date: bom.expiry_date ?? "",
      });
    }
  }, [bom, reset]);

  const onSubmit = async (data: FormData) => {
    const body = {
      version: data.version,
      effective_date: data.effective_date || null,
      expiry_date: data.expiry_date || null,
    };
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: bom!.id, ...body });
      } else {
        await createMut.mutateAsync({ productId, ...body });
      }
      onClose();
    } catch {
      // shown below
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
              {isEdit ? "Edit BOM" : "New BOM"}
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
                Version
              </label>
              <input
                {...register("version")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="1.0"
              />
              {errors.version && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.version.message}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Effective Date
                </label>
                <input
                  type="date"
                  {...register("effective_date")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Expiry Date
                </label>
                <input
                  type="date"
                  {...register("expiry_date")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
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
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                {isSubmitting ? "Saving…" : isEdit ? "Update" : "Create BOM"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
