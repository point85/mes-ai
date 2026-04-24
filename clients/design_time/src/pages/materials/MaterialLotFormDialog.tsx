/**
 * Material Lot Create / Edit dialog — modal form with Zod validation.
 *
 * Create: requires material_id, lot_number, quantity_on_hand (+ optional
 *   received_date, expiry_date, supplier).
 * Edit:   all fields plus status (available/reserved/consumed/expired).
 *   quantity_on_hand is typically changed via inventory transactions, but
 *   direct edit is allowed here for corrections.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateMaterialLot,
  useUpdateMaterialLot,
  useMaterials,
} from "../../hooks/useMaterial";
import type { MaterialLot } from "../../types";

const LOT_STATUSES = ["available", "reserved", "consumed", "expired"] as const;

const lotSchema = z.object({
  material_id: z.string().min(1, "Material is required"),
  lot_number: z
    .string()
    .min(1, "Lot number is required")
    .max(50)
    .refine((s) => !s.includes(" "), "Lot number must not contain spaces"),
  quantity_on_hand: z.coerce.number().min(0, "Quantity must be ≥ 0"),
  received_date: z.string().optional(),
  expiry_date: z.string().optional(),
  supplier: z.string().max(255).optional(),
  status: z.enum(LOT_STATUSES).optional(),
});

type LotFormData = z.infer<typeof lotSchema>;

interface Props {
  lot: MaterialLot | null;
  defaultMaterialId?: string;
  onClose: () => void;
}

function toDateInput(iso: string | null | undefined): string {
  if (!iso) return "";
  // Server returns ISO datetime or date; take first 10 chars for YYYY-MM-DD.
  return iso.slice(0, 10);
}

export default function MaterialLotFormDialog({ lot, defaultMaterialId, onClose }: Props) {
  const isEdit = !!lot;
  const createMut = useCreateMaterialLot();
  const updateMut = useUpdateMaterialLot();
  const { data: matResp } = useMaterials();
  const materials = (matResp?.data ?? [])
    .slice()
    .sort((a, b) => a.code.localeCompare(b.code));

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LotFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(lotSchema) as any,
    defaultValues: {
      material_id: defaultMaterialId ?? "",
      lot_number: "",
      quantity_on_hand: 0,
      received_date: "",
      expiry_date: "",
      supplier: "",
      status: "available",
    },
  });

  useEffect(() => {
    if (lot) {
      reset({
        material_id: lot.material_id,
        lot_number: lot.lot_number,
        quantity_on_hand: lot.quantity_on_hand,
        received_date: toDateInput(lot.received_date),
        expiry_date: toDateInput(lot.expiry_date),
        supplier: lot.supplier ?? "",
        status: (LOT_STATUSES as readonly string[]).includes(lot.status)
          ? (lot.status as (typeof LOT_STATUSES)[number])
          : "available",
      });
    }
  }, [lot, reset]);

  const onSubmit = async (data: LotFormData) => {
    const payload = {
      lot_number: data.lot_number,
      quantity_on_hand: data.quantity_on_hand,
      received_date: data.received_date ? data.received_date : null,
      expiry_date: data.expiry_date ? data.expiry_date : null,
      supplier: data.supplier?.trim() ? data.supplier.trim() : null,
    };
    try {
      if (isEdit) {
        await updateMut.mutateAsync({
          id: lot!.id,
          ...payload,
          status: data.status,
        });
      } else {
        await createMut.mutateAsync({
          material_id: data.material_id,
          ...payload,
        });
      }
      onClose();
    } catch {
      // Error shown via mutation state
    }
  };

  const mutError = createMut.error || updateMut.error;

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Material Lot" : "New Material Lot"}
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
                {...register("material_id")}
                disabled={isEdit}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100"
              >
                <option value="">— Select material —</option>
                {materials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.code} — {m.name} ({m.material_type})
                  </option>
                ))}
              </select>
              {errors.material_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.material_id.message}
                </p>
              )}
              {isEdit && (
                <p className="mt-1 text-xs text-gray-400">
                  Material cannot be changed after creation.
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Lot Number
                </label>
                <input
                  {...register("lot_number")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="LOT-2026-0001"
                />
                {errors.lot_number && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.lot_number.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Quantity on Hand
                </label>
                <input
                  type="number"
                  step="any"
                  {...register("quantity_on_hand")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.quantity_on_hand && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.quantity_on_hand.message}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Received Date <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="date"
                  {...register("received_date")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Expiry Date <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="date"
                  {...register("expiry_date")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Supplier <span className="text-gray-400">(optional)</span>
              </label>
              <input
                {...register("supplier")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="Acme Supplies, Inc."
              />
            </div>

            {isEdit && (
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Status
                </label>
                <select
                  {...register("status")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {LOT_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-400">
                  New lots default to <code>available</code>. Use this to
                  manually reserve, expire, or mark as consumed.
                </p>
              </div>
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
