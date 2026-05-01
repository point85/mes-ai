/**
 * BOM Item Create / Edit dialog — a single line item within a BOM.
 *
 * Fields:
 *   material_code      — picked from the materials catalog
 *   quantity           — positive number
 *   uom                — unit of measure string (defaulted from material)
 *   position           — sort order within the BOM
 *   process_segment_id — optional link to a route step where the material is consumed
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateBOMItem,
  useUpdateBOMItem,
} from "../../hooks/useProductDef";
import { useMaterials } from "../../hooks/useMaterial";
import { useUoMs } from "../../hooks/useUoM";
import type { BOMItem, RouteStep, Material } from "../../types";

const schema = z.object({
  material_code: z.string().min(1, "Material is required"),
  quantity: z
    .number({ invalid_type_error: "Quantity required" })
    .positive("Must be > 0"),
  uom_id: z.string().min(1, "UoM is required"),
  position: z.number().int().min(0).optional(),
  process_segment_id: z.string().nullable().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  bomId: string;
  item: BOMItem | null;
  steps: RouteStep[];
  onClose: () => void;
}

export default function BOMItemFormDialog({
  bomId,
  item,
  steps,
  onClose,
}: Props) {
  const isEdit = !!item;
  const createMut = useCreateBOMItem();
  const updateMut = useUpdateBOMItem();

  const { data: materialsResp } = useMaterials();
  const materials = materialsResp?.data ?? [];

  const { data: uomData } = useUoMs();
  const nonRateUoMs = (uomData?.data ?? []).filter((u) => u.uom_type !== "rate");

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      material_code: "",
      quantity: 1,
      uom_id: "",
      position: 0,
      process_segment_id: null,
    },
  });

  useEffect(() => {
    if (item) {
      reset({
        material_code: item.material_code,
        quantity: item.quantity,
        uom_id: item.uom_id,
        position: item.position,
        process_segment_id: item.process_segment_id ?? null,
      });
    }
  }, [item, reset]);

  // When material is chosen from the dropdown, auto-fill UoM from the material default
  const selectedMaterialCode = watch("material_code");
  useEffect(() => {
    if (!selectedMaterialCode) return;
    const m = materials.find((x: Material) => x.code === selectedMaterialCode);
    if (m && !isEdit) {
      setValue("uom_id", m.uom_id);
    }
  }, [selectedMaterialCode, materials, setValue, isEdit]);

  const onSubmit = async (data: FormData) => {
    const body = {
      material_code: data.material_code,
      quantity: Number(data.quantity),
      uom_id: data.uom_id,
      position: data.position ?? 0,
      process_segment_id: data.process_segment_id || null,
    };
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: item!.id, ...body });
      } else {
        await createMut.mutateAsync({ bomId, ...body });
      }
      onClose();
    } catch {
      // shown below
    }
  };

  const mutError = createMut.error || updateMut.error;

  const sortedSteps = [...steps].sort((a, b) => a.sequence - b.sequence);

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit BOM Item" : "New BOM Item"}
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
                Material
              </label>
              <select
                {...register("material_code")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— pick material —</option>
                {materials
                  .slice()
                  .sort((a: Material, b: Material) =>
                    a.code.localeCompare(b.code),
                  )
                  .map((m: Material) => (
                    <option key={m.id} value={m.code}>
                      {m.code} — {m.name}
                    </option>
                  ))}
              </select>
              {errors.material_code && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.material_code.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700">
                  Quantity
                </label>
                <input
                  type="number"
                  step="any"
                  {...register("quantity", { valueAsNumber: true })}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.quantity && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.quantity.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  UoM
                </label>
                <select
                  {...register("uom_id")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">— Select —</option>
                  {nonRateUoMs.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.symbol} — {u.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Position
                </label>
                <input
                  type="number"
                  {...register("position", { valueAsNumber: true })}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                <p className="mt-1 text-xs text-gray-400">
                  Sort order within the BOM
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Consumed at Step{" "}
                  <span className="text-gray-400">(optional)</span>
                </label>
                <select
                  {...register("process_segment_id")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">— none —</option>
                  {sortedSteps.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.sequence}. {s.name}
                    </option>
                  ))}
                </select>
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
                {isSubmitting ? "Saving…" : isEdit ? "Update" : "Create Item"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
