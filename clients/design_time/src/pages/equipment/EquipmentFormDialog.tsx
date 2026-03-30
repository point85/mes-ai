/**
 * Equipment Create / Edit dialog — modal form with Zod validation.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateEquipment, useUpdateEquipment } from "../../hooks/usePhysicalModel";
import { useStateModels } from "../../hooks/usePerformance";
import type { Equipment } from "../../types";

const equipSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  code: z
    .string()
    .min(1, "Code is required")
    .max(50)
    .refine((s) => !s.includes(" "), "Code must not contain spaces"),
  description: z.string().nullable().optional(),
  equipment_type: z.string().nullable().optional(),
  state_model_id: z.string().nullable().optional(),
  capabilities_json: z.string().optional(),
});

type EquipFormData = z.infer<typeof equipSchema>;

interface Props {
  equipment: Equipment | null;
  wcId: string;
  onClose: () => void;
}

export default function EquipmentFormDialog({ equipment, wcId, onClose }: Props) {
  const isEdit = !!equipment;
  const createMut = useCreateEquipment();
  const updateMut = useUpdateEquipment();
  const { data: stateModels } = useStateModels();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<EquipFormData>({
    resolver: zodResolver(equipSchema),
    defaultValues: {
      name: "",
      code: "",
      description: "",
      equipment_type: "",
      state_model_id: "",
      capabilities_json: "",
    },
  });

  useEffect(() => {
    if (equipment) {
      reset({
        name: equipment.name,
        code: equipment.code,
        description: equipment.description ?? "",
        equipment_type: equipment.equipment_type ?? "",
        state_model_id: equipment.state_model_id ?? "",
        capabilities_json: equipment.capabilities
          ? JSON.stringify(equipment.capabilities, null, 2)
          : "",
      });
    }
  }, [equipment, reset]);

  const onSubmit = async (data: EquipFormData) => {
    let capabilities: Record<string, unknown> | null = null;
    if (data.capabilities_json?.trim()) {
      try {
        capabilities = JSON.parse(data.capabilities_json);
      } catch {
        setError("capabilities_json", { message: "Invalid JSON" });
        return;
      }
    }

    const payload = {
      name: data.name,
      code: data.code,
      description: data.description,
      equipment_type: data.equipment_type || null,
      capabilities,
      state_model_id: data.state_model_id || null,
    };

    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: equipment!.id, ...payload });
      } else {
        await createMut.mutateAsync({ wcId, ...payload });
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
        <DialogPanel className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Equipment" : "New Equipment"}
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Code</label>
                <input
                  {...register("code")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="EQ-01"
                />
                {errors.code && (
                  <p className="mt-1 text-xs text-red-600">{errors.code.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Name</label>
                <input
                  {...register("name")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="CNC Mill #1"
                />
                {errors.name && (
                  <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Equipment Type <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  {...register("equipment_type")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="CNC, conveyor, sensor…"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  State Model <span className="text-gray-400">(optional)</span>
                </label>
                <select
                  {...register("state_model_id")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">None (100% available)</option>
                  {(stateModels ?? []).map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.name} ({m.model_id})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Assigns a state machine for availability tracking.
                </p>
              </div>
            </div>

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

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Capabilities JSON <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                {...register("capabilities_json")}
                rows={3}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder='{"max_speed": 1000, "axes": 5}'
              />
              {errors.capabilities_json && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.capabilities_json.message}
                </p>
              )}
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
                {isSubmitting ? "Saving…" : isEdit ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
