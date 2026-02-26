/**
 * CounterFormDialog — create / update a production counter record.
 */

import { useEffect } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useCreateOrUpdateCounter } from "../../hooks/usePerformance";

const schema = z.object({
  equipment_id: z.string().min(1, "Required"),
  order_id: z.string().optional(),
  shift_date: z.string().min(1, "Required"),
  good_count: z.coerce.number().int().min(0),
  reject_count: z.coerce.number().int().min(0),
  rework_count: z.coerce.number().int().min(0),
  ideal_cycle_time_sec: z.coerce.number().positive().optional(),
  actual_run_time_sec: z.coerce.number().positive().optional(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  onClose: () => void;
}

export default function CounterFormDialog({ onClose }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      equipment_id: "",
      order_id: "",
      shift_date: new Date().toISOString().slice(0, 10),
      good_count: 0,
      reject_count: 0,
      rework_count: 0,
    },
  });

  useEffect(() => {
    reset();
  }, [reset]);

  const mutation = useCreateOrUpdateCounter();

  const onSubmit = async (values: FormValues) => {
    const body: any = { ...values };
    if (!body.order_id) delete body.order_id;
    if (body.ideal_cycle_time_sec === undefined) delete body.ideal_cycle_time_sec;
    if (body.actual_run_time_sec === undefined) delete body.actual_run_time_sec;
    await mutation.mutateAsync(body);
    onClose();
  };

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <DialogTitle className="text-lg font-semibold text-gray-900 mb-4">
            Record Production Counter
          </DialogTitle>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* equipment_id */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Equipment ID *
              </label>
              <input
                {...register("equipment_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
              {errors.equipment_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.equipment_id.message}
                </p>
              )}
            </div>

            {/* order_id */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Order ID
              </label>
              <input
                {...register("order_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            {/* shift_date */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Shift Date *
              </label>
              <input
                type="date"
                {...register("shift_date")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
              {errors.shift_date && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.shift_date.message}
                </p>
              )}
            </div>

            {/* counts row */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Good
                </label>
                <input
                  type="number"
                  min={0}
                  {...register("good_count")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Reject
                </label>
                <input
                  type="number"
                  min={0}
                  {...register("reject_count")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Rework
                </label>
                <input
                  type="number"
                  min={0}
                  {...register("rework_count")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* cycle / run times */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Ideal Cycle (s)
                </label>
                <input
                  type="number"
                  step="0.01"
                  {...register("ideal_cycle_time_sec")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Actual Run (s)
                </label>
                <input
                  type="number"
                  step="0.01"
                  {...register("actual_run_time_sec")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* actions */}
            <div className="flex justify-end gap-3 pt-2">
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
                {isSubmitting ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
