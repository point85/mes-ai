/**
 * Create / Edit dialog for an Equipment Class.
 */

import { useForm } from "react-hook-form";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateEquipmentClass,
  useUpdateEquipmentClass,
} from "../../hooks/usePhysicalModel";
import type { EquipmentClass } from "../../types";

interface Props {
  existing: EquipmentClass | null;
  onClose: () => void;
}

interface FormValues {
  name: string;
  code: string;
  description: string;
}

export default function EquipmentClassFormDialog({ existing, onClose }: Props) {
  const createMut = useCreateEquipmentClass();
  const updateMut = useUpdateEquipmentClass();

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      name: existing?.name ?? "",
      code: existing?.code ?? "",
      description: existing?.description ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      name: values.name,
      code: values.code,
      description: values.description || null,
    };
    if (existing) {
      await updateMut.mutateAsync({ id: existing.id, ...payload });
    } else {
      await createMut.mutateAsync(payload);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {existing ? "Edit Equipment Class" : "New Equipment Class"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              {...register("name", { required: "Name is required" })}
              className="w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              placeholder="e.g. Mixer"
            />
            {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Code</label>
            <input
              {...register("code", { required: "Code is required" })}
              className="w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
              placeholder="e.g. MIXER"
            />
            {errors.code && <p className="text-xs text-red-600 mt-1">{errors.code.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              {...register("description")}
              rows={2}
              className="w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              placeholder="Optional description"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" className="px-3 py-2 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700">
              {existing ? "Save" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
