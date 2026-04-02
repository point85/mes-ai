/**
 * Step Create / Edit dialog — creates or edits a route step.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateRouteStep, useUpdateRouteStep } from "../../hooks/useProductDef";
import type { RouteStep } from "../../types";

const schema = z.object({
  sequence: z.number().int().min(1, "Sequence ≥ 1"),
  name: z.string().min(1, "Name is required").max(255),
  step_type: z.enum(["standard", "inspection", "rework", "mrb"]),
  expected_cycle_time_sec: z.number().min(0).nullable().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  routeId: string;
  step: RouteStep | null;
  onClose: () => void;
}

export default function StepFormDialog({ routeId, step, onClose }: Props) {
  const isEdit = !!step;
  const createMut = useCreateRouteStep();
  const updateMut = useUpdateRouteStep();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      sequence: 10,
      name: "",
      step_type: "standard",
      expected_cycle_time_sec: null,
    },
  });

  useEffect(() => {
    if (step) {
      reset({
        sequence: step.sequence,
        name: step.name,
        step_type: step.step_type as "standard" | "inspection" | "rework" | "mrb",
        expected_cycle_time_sec: step.expected_cycle_time_sec,
      });
    }
  }, [step, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: step!.id, ...data });
      } else {
        await createMut.mutateAsync({ routeId, ...data });
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
              {isEdit ? "Edit Step" : "New Step"}
            </DialogTitle>
            <button onClick={onClose} className="rounded p-1 text-gray-400 hover:text-gray-600">
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
                <label className="block text-sm font-medium text-gray-700">Sequence</label>
                <input
                  type="number"
                  {...register("sequence")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                {errors.sequence && (
                  <p className="mt-1 text-xs text-red-600">{errors.sequence.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Type</label>
                <select
                  {...register("step_type")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="standard">Standard</option>
                  <option value="inspection">Inspection</option>
                  <option value="rework">Rework</option>
                  <option value="mrb">MRB</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                {...register("name")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="Assembly"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Expected Cycle Time (sec) <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="number"
                {...register("expected_cycle_time_sec")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="120"
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
