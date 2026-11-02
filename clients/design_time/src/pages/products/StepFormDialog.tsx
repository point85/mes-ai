/**
 * Step Create / Edit dialog — creates or edits a route step.
 */

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { MagnifyingGlassIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateRouteStep, useUpdateRouteStep, useDispositions } from "../../hooks/useProductDef";
import { useStorageLocations } from "../../hooks/useInventory";
import LocationSearchDialog from "../../components/LocationSearchDialog";
import type { RouteStep } from "../../types";
import EquipmentRequirementsEditor from "./EquipmentRequirementsEditor";
import MaterialRequirementsEditor from "./MaterialRequirementsEditor";
import StepParameterEditor from "./StepParameterEditor";
import StepDataDefinitionEditor from "./StepDataDefinitionEditor";

const schema = z.object({
  sequence: z.number().int().min(1, "Sequence ≥ 1"),
  name: z.string().min(1, "Name is required").max(255),
  step_type: z.enum(["production", "inspection", "rework", "mrb"]),
  expected_cycle_time_sec: z.number().min(0).nullable().optional(),
  erp_operation_number: z.string().max(50).nullable().optional(),
  is_initial_step: z.boolean().optional(),
  transfer_location_id: z.string().nullable().optional(),
  input_disposition_ids: z.array(z.string()).default([]),
  output_disposition_ids: z.array(z.string()).default([]),
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
  const { data: dispResp } = useDispositions();
  const dispositions = dispResp?.data ?? [];
  const { data: locResp } = useStorageLocations();
  const [locationSearchOpen, setLocationSearchOpen] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      sequence: 10,
      name: "",
      step_type: "production",
      expected_cycle_time_sec: null,
      erp_operation_number: null,
      is_initial_step: false,
      transfer_location_id: null,
      input_disposition_ids: [],
      output_disposition_ids: [],
    },
  });

  useEffect(() => {
    if (step) {
      reset({
        sequence: step.sequence,
        name: step.name,
        step_type: step.step_type as "production" | "inspection" | "rework" | "mrb",
        expected_cycle_time_sec: step.expected_cycle_time_sec,
        erp_operation_number: step.erp_operation_number,
        is_initial_step: step.is_initial_step,
        transfer_location_id: step.transfer_location_id ?? null,
        input_disposition_ids: (step.input_dispositions ?? []).map((d) => d.id),
        output_disposition_ids: (step.output_dispositions ?? []).map((d) => d.id),
      });
    }
  }, [step, reset]);

  // Only routing-category dispositions may be wired into the input/output
  // lists; hold/scrap dispositions are workflow concerns, not graph edges.
  const routeDispositions = dispositions.filter((d) => d.category === "route");
  const transferLocationId = watch("transfer_location_id") ?? null;
  const transferLocation = (locResp?.data ?? []).find((l) => l.id === transferLocationId);
  const inputIds = watch("input_disposition_ids") ?? [];
  const outputIds = watch("output_disposition_ids") ?? [];

  const toggleDisposition = (
    field: "input_disposition_ids" | "output_disposition_ids",
    id: string,
  ) => {
    const current = field === "input_disposition_ids" ? inputIds : outputIds;
    const next = current.includes(id)
      ? current.filter((x) => x !== id)
      : [...current, id];
    setValue(field, next, { shouldDirty: true });
  };

  const onSubmit = async (data: FormData) => {
    try {
      const payload = {
        ...data,
        is_initial_step: !!data.is_initial_step,
        transfer_location_id: data.transfer_location_id ?? null,
        input_disposition_ids: data.input_disposition_ids ?? [],
        output_disposition_ids: data.output_disposition_ids ?? [],
      };
      if (isEdit) {
        await updateMut.mutateAsync({ id: step!.id, ...payload });
      } else {
        await createMut.mutateAsync({ routeId, ...payload });
      }
      onClose();
    } catch {
      // error shown via mutation state
    }
  };

  const mutError = createMut.error || updateMut.error;

  return (
    <>
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center overflow-auto p-4">
        <DialogPanel className="w-[42rem] min-w-[24rem] min-h-[20rem] max-h-[90vh] resize overflow-auto rounded-xl bg-white p-6 shadow-xl">
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
                  {...register("sequence", { valueAsNumber: true })}
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
                  <option value="production">Production</option>
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
            {isEdit && step && (
              <EquipmentRequirementsEditor
                stepId={step.id}
                primaryEquipmentClassId={step.equipment_class_id}
              />
            )}
            {isEdit && step && (
              <MaterialRequirementsEditor stepId={step.id} routeId={routeId} />
            )}
            {isEdit && step && (
              <StepParameterEditor stepId={step.id} />
            )}
            {isEdit && step && (
              <StepDataDefinitionEditor stepId={step.id} />
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Expected Cycle Time (sec) <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="number"
                {...register("expected_cycle_time_sec", { valueAsNumber: true })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="120"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                ERP Operation # <span className="text-gray-400">(optional)</span>
              </label>
              <input
                {...register("erp_operation_number")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="0010"
              />
            </div>
            <div className="flex items-start gap-2">
              <input
                id="is_initial_step"
                type="checkbox"
                {...register("is_initial_step")}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <div>
                <label htmlFor="is_initial_step" className="block text-sm font-medium text-gray-700">
                  Initial step
                </label>
                <p className="text-xs text-gray-400">
                  Mark as the canonical entry point of the route. An initial step
                  must have an empty input disposition list.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-md border border-gray-200 bg-gray-50 p-3">
              <div>
                <p className="text-sm font-medium text-gray-700">
                  Input Dispositions
                </p>
                <p className="mb-2 text-xs text-gray-500">
                  Dispositions that route WIP <em>into</em> this step.
                  Only routing-category dispositions are available.
                </p>
                {routeDispositions.length === 0 ? (
                  <p className="text-xs italic text-gray-400">
                    No routing-category dispositions defined yet.
                  </p>
                ) : (
                  <ul className="max-h-40 space-y-1 overflow-y-auto rounded border border-gray-200 bg-white p-2">
                    {routeDispositions.map((d) => {
                      const checked = inputIds.includes(d.id);
                      return (
                        <li key={d.id} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleDisposition("input_disposition_ids", d.id)}
                            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                          />
                          <span className="text-xs text-gray-700">
                            <span className="font-mono">{d.code}</span> — {d.name}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700">
                  Output Dispositions
                </p>
                <p className="mb-2 text-xs text-gray-500">
                  Dispositions that route WIP <em>out of</em> this step.
                  Only routing-category dispositions are available.
                </p>
                {routeDispositions.length === 0 ? (
                  <p className="text-xs italic text-gray-400">
                    No routing-category dispositions defined yet.
                  </p>
                ) : (
                  <ul className="max-h-40 space-y-1 overflow-y-auto rounded border border-gray-200 bg-white p-2">
                    {routeDispositions.map((d) => {
                      const checked = outputIds.includes(d.id);
                      return (
                        <li key={d.id} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleDisposition("output_disposition_ids", d.id)}
                            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                          />
                          <span className="text-xs text-gray-700">
                            <span className="font-mono">{d.code}</span> — {d.name}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Transfer Location <span className="text-gray-400">(optional)</span>
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  readOnly
                  aria-label="Transfer location"
                  value={transferLocation ? `${transferLocation.code} - ${transferLocation.name}` : ""}
                  placeholder="None"
                  className="block w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm shadow-sm"
                />
                <button
                  type="button"
                  aria-label="Find transfer location"
                  onClick={() => setLocationSearchOpen(true)}
                  className="rounded-md border border-gray-300 bg-white px-3 text-gray-600 hover:bg-gray-50"
                >
                  <MagnifyingGlassIcon className="h-5 w-5" />
                </button>
                {transferLocationId && (
                  <button
                    type="button"
                    aria-label="Clear transfer location"
                    onClick={() => setValue("transfer_location_id", null, { shouldDirty: true })}
                    className="rounded-md border border-gray-300 bg-white px-3 text-gray-600 hover:bg-gray-50"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                )}
              </div>
              <p className="mt-1 text-xs text-gray-400">
                WIP completed from this step can be transferred to this inventory location.
              </p>
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
    <LocationSearchDialog
      open={locationSearchOpen}
      onClose={() => setLocationSearchOpen(false)}
      onSelect={(loc) => setValue("transfer_location_id", loc.id, { shouldDirty: true })}
    />
    </>
  );
}
