/**
 * Create / Edit dialog for an Equipment Class Property.
 */

import { useForm } from "react-hook-form";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateClassProperty,
  useUpdateClassProperty,
} from "../../hooks/usePhysicalModel";
import type { EquipmentClassProperty } from "../../types";

interface Props {
  classId: string;
  existing: EquipmentClassProperty | null;
  onClose: () => void;
}

interface FormValues {
  name: string;
  description: string;
  data_type: string;
  uom_id: string;
  default_value: string;
}

const DATA_TYPES = ["string", "float", "int", "boolean"];

export default function ClassPropertyFormDialog({ classId, existing, onClose }: Props) {
  const createMut = useCreateClassProperty();
  const updateMut = useUpdateClassProperty();

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      name: existing?.name ?? "",
      description: existing?.description ?? "",
      data_type: existing?.data_type ?? "string",
      uom_id: existing?.uom_id ?? "",
      default_value: existing?.default_value ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      name: values.name,
      description: values.description || null,
      data_type: values.data_type,
      uom_id: values.uom_id || null,
      default_value: values.default_value || null,
    };
    if (existing) {
      await updateMut.mutateAsync({ id: existing.id, ...payload });
    } else {
      await createMut.mutateAsync({ classId, ...payload });
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {existing ? "Edit Property" : "Add Property"}
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
              placeholder="e.g. max_speed"
            />
            {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Type</label>
            <select
              {...register("data_type")}
              className="w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            >
              {DATA_TYPES.map((dt) => (
                <option key={dt} value={dt}>{dt}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">UoM</label>
            <input
              {...register("uom_id")}
              className="w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
              placeholder="e.g. bottles/min"
            />
            <p className="text-xs text-gray-400 mt-1">Unit of measure symbol (optional)</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Value</label>
            <input
              {...register("default_value")}
              className="w-full rounded border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              placeholder="Optional"
            />
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
