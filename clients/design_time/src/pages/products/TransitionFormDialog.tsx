/**
 * Transition Create / Edit dialog — creates or edits a step transition.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateStepTransition,
  useUpdateStepTransition,
} from "../../hooks/useProductDef";
import type { RouteStep, StepTransition } from "../../types";

const schema = z
  .object({
    to_step_id: z.string().min(1, "Target step is required"),
    condition: z.enum(["always", "on_pass", "on_fail", "on_rework", "disposition"]),
    is_default: z.boolean().optional(),
    priority: z.number().int().min(0).optional(),
    label: z.string().max(255).nullable().optional(),
  })
  .refine(
    (d) => d.condition !== "disposition" || (d.label && d.label.trim().length > 0),
    { message: "Label is required for disposition conditions", path: ["label"] },
  );

type FormData = z.infer<typeof schema>;

interface Props {
  stepId: string;
  transition: StepTransition | null;
  steps: RouteStep[];
  onClose: () => void;
}

export default function TransitionFormDialog({
  stepId,
  transition,
  steps,
  onClose,
}: Props) {
  const isEdit = !!transition;
  const createMut = useCreateStepTransition();
  const updateMut = useUpdateStepTransition();

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      to_step_id: "",
      condition: "always",
      is_default: false,
      priority: 0,
      label: "",
    },
  });

  const condition = watch("condition");

  useEffect(() => {
    if (transition) {
      reset({
        to_step_id: transition.to_step_id,
        condition: transition.condition as FormData["condition"],
        is_default: transition.is_default,
        priority: transition.priority,
        label: transition.label ?? "",
      });
    }
  }, [transition, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      const body = {
        ...data,
        label: data.condition === "disposition" ? data.label : null,
      };
      if (isEdit) {
        await updateMut.mutateAsync({ id: transition!.id, ...body });
      } else {
        await createMut.mutateAsync({ stepId, ...body });
      }
      onClose();
    } catch {
      // error shown via mutation state
    }
  };

  const mutError = createMut.error || updateMut.error;

  // Filter target steps — can't transition to self
  const targetSteps = steps.filter((s) => s.id !== stepId);

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Transition" : "New Transition"}
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
            {/* Target step */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Target Step
              </label>
              <select
                {...register("to_step_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">Select a step…</option>
                {targetSteps.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.sequence}. {s.name} ({s.step_type})
                  </option>
                ))}
              </select>
              {errors.to_step_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.to_step_id.message}
                </p>
              )}
            </div>

            {/* Condition */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Condition
              </label>
              <select
                {...register("condition")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="always">Always (unconditional)</option>
                <option value="on_pass">On Pass</option>
                <option value="on_fail">On Fail</option>
                <option value="on_rework">On Rework</option>
                <option value="disposition">Disposition (operator choice)</option>
              </select>
            </div>

            {/* Label — only shown for disposition */}
            {condition === "disposition" && (
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Disposition Label
                </label>
                <input
                  {...register("label")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="e.g. Return to rework, Scrap, Resume"
                />
                {errors.label && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.label.message}
                  </p>
                )}
              </div>
            )}

            {/* Priority & Default */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Priority
                </label>
                <input
                  type="number"
                  {...register("priority")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="0"
                />
                <p className="mt-0.5 text-[11px] text-gray-400">
                  Higher = evaluated first
                </p>
              </div>
              <div className="flex items-end pb-6">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    {...register("is_default")}
                    className="rounded border-gray-300"
                  />
                  Default fallback
                </label>
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
