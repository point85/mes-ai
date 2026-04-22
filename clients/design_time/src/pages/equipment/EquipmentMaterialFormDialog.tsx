/**
 * Equipment Material Setup Create / Edit dialog — modal form.
 */

import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateEquipmentMaterial,
  useUpdateEquipmentMaterial,
} from "../../hooks/usePhysicalModel";
import { useMaterials } from "../../hooks/useMaterial";
import { useUoMs } from "../../hooks/useUoM";
import type { EquipmentMaterial } from "../../types";

const schema = z.object({
  material_id: z.string().min(1, "Material is required"),
  design_speed: z.number().positive("Must be > 0"),
  design_speed_uom: z.string().min(1, "Speed UoM is required"),
  reject_uom: z.string().min(1, "Reject UoM is required"),
  target_oee: z.number().min(0, "Min 0").max(100, "Max 100"),
});

type FormData = z.infer<typeof schema>;

interface Props {
  setup: EquipmentMaterial | null;
  equipId: string;
  onClose: () => void;
}

export default function EquipmentMaterialFormDialog({
  setup,
  equipId,
  onClose,
}: Props) {
  const isEdit = !!setup;
  const createMut = useCreateEquipmentMaterial();
  const updateMut = useUpdateEquipmentMaterial();

  const { data: matData } = useMaterials();
  const { data: uomData } = useUoMs();

  const materialOptions = useMemo(
    () => (matData?.data ?? []).map((m) => ({ id: m.id, label: `${m.code} — ${m.name}` })),
    [matData],
  );

  const rateUoMs = useMemo(
    () => (uomData?.data ?? []).filter((u) => u.uom_type === "rate"),
    [uomData],
  );
  const nonRateUoMs = useMemo(
    () => (uomData?.data ?? []).filter((u) => u.uom_type !== "rate"),
    [uomData],
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      material_id: "",
      design_speed: 0,
      design_speed_uom: "",
      reject_uom: "",
      target_oee: 85,
    },
  });

  useEffect(() => {
    if (setup) {
      reset({
        material_id: setup.material_id,
        design_speed: setup.design_speed,
        design_speed_uom: setup.design_speed_uom,
        reject_uom: setup.reject_uom,
        target_oee: setup.target_oee,
      });
    }
  }, [setup, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEdit) {
        await updateMut.mutateAsync({
          id: setup!.id,
          design_speed: data.design_speed,
          design_speed_uom: data.design_speed_uom,
          reject_uom: data.reject_uom,
          target_oee: data.target_oee,
        });
      } else {
        await createMut.mutateAsync({ equipId, ...data });
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
              {isEdit ? "Edit Material Setup" : "New Material Setup"}
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
            {/* Material selector (disabled on edit — can't change the material) */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Material
              </label>
              <select
                {...register("material_id")}
                disabled={isEdit}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100"
              >
                <option value="">Select a material…</option>
                {materialOptions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
              {errors.material_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.material_id.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Design speed */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Design Speed
                </label>
                <input
                  type="number"
                  step="any"
                  {...register("design_speed", { valueAsNumber: true })}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="120"
                />
                {errors.design_speed && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.design_speed.message}
                  </p>
                )}
              </div>

              {/* Design speed UoM (rate UoMs only) */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Speed UoM
                </label>
                <select
                  {...register("design_speed_uom")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">Select rate UoM…</option>
                  {rateUoMs.map((u) => (
                    <option key={u.symbol} value={u.symbol}>
                      {u.symbol} — {u.name}
                    </option>
                  ))}
                </select>
                {errors.design_speed_uom && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.design_speed_uom.message}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Reject UoM */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Reject UoM
                </label>
                <select
                  {...register("reject_uom")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">Select UoM…</option>
                  {nonRateUoMs.map((u) => (
                    <option key={u.symbol} value={u.symbol}>
                      {u.symbol} — {u.name}
                    </option>
                  ))}
                </select>
                {errors.reject_uom && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.reject_uom.message}
                  </p>
                )}
              </div>

              {/* Target OEE */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Target OEE (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  {...register("target_oee", { valueAsNumber: true })}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="85"
                />
                {errors.target_oee && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.target_oee.message}
                  </p>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
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
