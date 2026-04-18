/**
 * Production Order Create / Edit dialog — modal form with Zod validation.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateOrder, useUpdateOrder } from "../../hooks/useProduction";
import { useProducts } from "../../hooks/useProductDef";
import type { ProductionOrder } from "../../types";

const orderSchema = z.object({
  order_number: z.string().min(1, "Order number is required").max(100),
  product_id: z.string().min(1, "Product ID is required"),
  route_id: z.string().nullable().optional(),
  quantity_ordered: z.coerce.number().int().positive("Must be > 0"),
  priority: z.coerce.number().int().min(0),
  planned_start: z.string().nullable().optional(),
  planned_end: z.string().nullable().optional(),
  erp_reference: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
});

type OrderFormData = z.infer<typeof orderSchema>;

interface Props {
  order: ProductionOrder | null;
  onClose: () => void;
}

export default function OrderFormDialog({ order, onClose }: Props) {
  const isEdit = !!order;
  const createMut = useCreateOrder();
  const updateMut = useUpdateOrder();
  const { data: productsResp } = useProducts();
  const products = productsResp?.data ?? [];

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<OrderFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(orderSchema) as any,
    defaultValues: {
      order_number: "",
      product_id: "",
      route_id: "",
      quantity_ordered: 1,
      priority: 0,
      planned_start: "",
      planned_end: "",
      erp_reference: "",
      notes: "",
    },
  });

  useEffect(() => {
    if (order) {
      reset({
        order_number: order.order_number,
        product_id: order.product_id,
        route_id: order.route_id ?? "",
        quantity_ordered: order.quantity_ordered,
        priority: order.priority,
        planned_start: order.planned_start
          ? order.planned_start.slice(0, 16)
          : "",
        planned_end: order.planned_end
          ? order.planned_end.slice(0, 16)
          : "",
        erp_reference: order.erp_reference ?? "",
        notes: order.notes ?? "",
      });
    }
  }, [order, reset]);

  const onSubmit = async (data: OrderFormData) => {
    try {
      const payload = {
        ...data,
        route_id: data.route_id || null,
        planned_start: data.planned_start || null,
        planned_end: data.planned_end || null,
        erp_reference: data.erp_reference || null,
        notes: data.notes || null,
      };
      if (isEdit) {
        await updateMut.mutateAsync({ id: order!.id, ...payload });
      } else {
        await createMut.mutateAsync(payload);
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
              {isEdit ? "Edit Order" : "New Production Order"}
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
                <label className="block text-sm font-medium text-gray-700">
                  Order Number
                </label>
                <input
                  {...register("order_number")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="ORD-2026-001"
                />
                {errors.order_number && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.order_number.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Priority
                </label>
                <input
                  type="number"
                  {...register("priority")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Product
              </label>
              <select
                {...register("product_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— Select a product —</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
              {errors.product_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.product_id.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Quantity
                </label>
                <input
                  type="number"
                  {...register("quantity_ordered")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.quantity_ordered && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.quantity_ordered.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Route ID{" "}
                  <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  {...register("route_id")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="UUID"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Planned Start{" "}
                  <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="datetime-local"
                  {...register("planned_start")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Planned End{" "}
                  <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="datetime-local"
                  {...register("planned_end")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                ERP Reference{" "}
                <span className="text-gray-400">(optional)</span>
              </label>
              <input
                {...register("erp_reference")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="SAP order number"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Notes{" "}
                <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                {...register("notes")}
                rows={2}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
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
