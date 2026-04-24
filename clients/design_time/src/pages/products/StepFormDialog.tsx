/**
 * Step Create / Edit dialog — creates or edits a route step.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateRouteStep, useUpdateRouteStep, useDispositions } from "../../hooks/useProductDef";
import { useAllWorkCells, useAllLines, useEquipmentClasses } from "../../hooks/usePhysicalModel";
import type { RouteStep } from "../../types";
import EquipmentRequirementsEditor from "./EquipmentRequirementsEditor";
import StepParameterEditor from "./StepParameterEditor";

const schema = z.object({
  sequence: z.number().int().min(1, "Sequence ≥ 1"),
  name: z.string().min(1, "Name is required").max(255),
  step_type: z.enum(["production", "inspection", "rework", "mrb"]),
  work_cell_id: z.string().nullable().optional(),
  equipment_class_id: z.string().nullable().optional(),
  expected_cycle_time_sec: z.number().min(0).nullable().optional(),
  erp_operation_number: z.string().max(50).nullable().optional(),
  disposition_id: z.string().nullable().optional(),
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
  const { data: wcResp } = useAllWorkCells();
  const workCells = (wcResp?.data ?? []).sort((a, b) => a.code.localeCompare(b.code));
  const { data: linesResp } = useAllLines();
  const allLines = linesResp?.data ?? [];
  const lineMap = new Map(allLines.map((ln) => [ln.id, ln]));
  const { data: ecResp } = useEquipmentClasses();
  const equipmentClasses = (ecResp?.data ?? []).sort((a: { code: string }, b: { code: string }) => a.code.localeCompare(b.code));

  // Group work cells by production line for the dropdown
  const wcByLine = new Map<string, typeof workCells>();
  for (const wc of workCells) {
    const group = wcByLine.get(wc.line_id) ?? [];
    group.push(wc);
    wcByLine.set(wc.line_id, group);
  }

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
      step_type: "production",
      work_cell_id: null,
      equipment_class_id: null,
      expected_cycle_time_sec: null,
      erp_operation_number: null,
      disposition_id: null,
    },
  });

  useEffect(() => {
    if (step) {
      reset({
        sequence: step.sequence,
        name: step.name,
        step_type: step.step_type as "production" | "inspection" | "rework" | "mrb",
        work_cell_id: step.work_cell_id,
        equipment_class_id: step.equipment_class_id,
        expected_cycle_time_sec: step.expected_cycle_time_sec,
        erp_operation_number: step.erp_operation_number,
        disposition_id: step.disposition_id,
      });
    }
  }, [step, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      const payload = {
        ...data,
        work_cell_id: data.work_cell_id || null,
        equipment_class_id: data.equipment_class_id || null,
        disposition_id: data.disposition_id || null,
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
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
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
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Work Cell <span className="text-gray-400">(optional)</span>
              </label>
              <select
                {...register("work_cell_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— None —</option>
                {[...wcByLine.entries()]
                  .sort(([a], [b]) => (lineMap.get(a)?.code ?? "").localeCompare(lineMap.get(b)?.code ?? ""))
                  .map(([lineId, cells]) => (
                    <optgroup key={lineId} label={lineMap.get(lineId)?.code ?? "Unknown Line"}>
                      {cells.map((wc) => (
                        <option key={wc.id} value={wc.id}>
                          {wc.code} — {wc.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">Where this step is performed</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Equipment Class <span className="text-gray-400">(ISA-95)</span>
              </label>
              <select
                {...register("equipment_class_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— None —</option>
                {equipmentClasses.map((ec: { id: string; code: string; name: string }) => (
                  <option key={ec.id} value={ec.id}>
                    {ec.code} — {ec.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">What class of equipment is needed (dispatch uses this)</p>
            </div>
            {isEdit && step && (
              <EquipmentRequirementsEditor stepId={step.id} />
            )}
            {isEdit && step && (
              <StepParameterEditor stepId={step.id} />
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
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Input Disposition <span className="text-gray-400">(optional)</span>
              </label>
              <select
                {...register("disposition_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— None —</option>
                {dispositions.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name} ({d.category})
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">Disposition that routes WIP to this step</p>
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
