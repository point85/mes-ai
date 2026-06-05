/**
 * Data Definition Create / Edit dialog — modal form with Zod validation.
 */

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import {
  useCreateDataDefinition,
  useUpdateDataDefinition,
} from "../../hooks/useDataCollection";
import {
  useAllRoutes,
  useRouteSteps,
} from "../../hooks/useProductDef";
import { useUoMs } from "../../hooks/useUoM";
import type { DataDefinition } from "../../types";

const dataDefSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  code: z
    .string()
    .min(1, "Code is required")
    .max(50)
    .refine((s) => !s.includes(" "), "Code must not contain spaces"),
  description: z.string().nullable().optional(),
  data_type: z.enum(["numeric", "string", "boolean", "enum"]),
  uom_id: z.string().nullable().optional(),
  step_id: z.string().nullable().optional(),
  source: z.enum(["manual", "equipment", "sensor"]),
  is_required: z.boolean(),
  enum_values: z.string().nullable().optional(),
  lower_limit: z.coerce.number().nullable().optional(),
  upper_limit: z.coerce.number().nullable().optional(),
});

type DataDefFormData = z.infer<typeof dataDefSchema>;

interface Props {
  definition: DataDefinition | null;
  onClose: () => void;
}

export default function DataDefFormDialog({ definition, onClose }: Props) {
  const isEdit = !!definition;
  const createMut = useCreateDataDefinition();
  const updateMut = useUpdateDataDefinition();

  const [selectedRouteId, setSelectedRouteId] = useState("");
  const { data: routesData } = useAllRoutes();
  const { data: stepsData } = useRouteSteps(selectedRouteId);
  const routes = routesData?.data ?? [];
  const steps = stepsData?.data ?? [];

  const { data: uomData } = useUoMs();
  const nonRateUoMs = (uomData?.data ?? []).filter((u) => u.uom_type !== "rate");

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<DataDefFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(dataDefSchema) as any,
    defaultValues: {
      name: "",
      code: "",
      description: "",
      data_type: "numeric",
      uom_id: "",
      step_id: null,
      source: "manual",
      is_required: false,
      enum_values: "",
      lower_limit: null,
      upper_limit: null,
    },
  });

  const dataType = watch("data_type");

  useEffect(() => {
    if (definition) {
      reset({
        name: definition.name,
        code: definition.code,
        description: definition.description ?? "",
        data_type: definition.data_type as
          | "numeric"
          | "string"
          | "boolean"
          | "enum",
        uom_id: definition.uom_id ?? "",
        step_id: definition.step_id ?? null,
        source: definition.source as "manual" | "equipment" | "sensor",
        is_required: definition.is_required,
        enum_values: definition.enum_values ?? "",
        lower_limit: definition.lower_limit,
        upper_limit: definition.upper_limit,
      });
    }
  }, [definition, reset]);

  // When editing, find which route owns the step so we can pre-select the route dropdown
  useEffect(() => {
    if (definition?.step_id && routes.length > 0 && !selectedRouteId) {
      // We don't know which route the step belongs to, so try each
      // The step's route_id isn't on the definition — we'll search all routes
      // For now set selectedRouteId to first route and let user adjust;
      // Once steps load, the step_id will match
      for (const r of routes) {
        // We'll set the first route and let the step query cascade
        setSelectedRouteId(r.id);
        break;
      }
    }
  }, [definition, routes, selectedRouteId]);

  const onSubmit = async (data: DataDefFormData) => {
    try {
      // Clean up null-ish values
      const payload = {
        ...data,
        uom_id: data.uom_id || null,
        step_id: data.step_id || null,
        enum_values: data.enum_values || null,
        lower_limit: data.lower_limit ?? null,
        upper_limit: data.upper_limit ?? null,
      };
      if (isEdit) {
        await updateMut.mutateAsync({ id: definition!.id, ...payload });
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
              {isEdit ? "Edit Data Definition" : "New Data Definition"}
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
                  Code
                </label>
                <input
                  {...register("code")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="TEMP-01"
                />
                {errors.code && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.code.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Source
                </label>
                <select
                  {...register("source")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="manual">Manual</option>
                  <option value="equipment">Equipment</option>
                  <option value="sensor">Sensor</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                {...register("name")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="Furnace Temperature"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.name.message}
                </p>
              )}
            </div>

            {/* Route Step — optional link to a specific route step */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Route <span className="text-gray-400">(opt)</span>
                </label>
                <select
                  value={selectedRouteId}
                  onChange={(e) => {
                    setSelectedRouteId(e.target.value);
                    setValue("step_id", null);
                  }}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">— Select route —</option>
                  {routes.map((r) => (
                    <option key={r.id} value={r.id}>{r.name} ({r.version})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Step <span className="text-gray-400">(opt)</span>
                </label>
                <select
                  {...register("step_id")}
                  disabled={!selectedRouteId}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100 disabled:text-gray-400"
                >
                  <option value="">— Any step —</option>
                  {steps.map((s) => (
                    <option key={s.id} value={s.id}>#{s.sequence} — {s.name}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-400">Collect at this step only (blank = any step)</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Data Type
                </label>
                <select
                  {...register("data_type")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="numeric">Numeric</option>
                  <option value="string">String</option>
                  <option value="boolean">Boolean</option>
                  <option value="enum">Enum</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  UoM{" "}
                  <span className="text-gray-400">(opt)</span>
                </label>
                <select
                  {...register("uom_id")}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">— none —</option>
                  {nonRateUoMs.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.symbol} — {u.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    {...register("is_required")}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Required
                </label>
              </div>
            </div>

            {/* Numeric limits — only show for numeric type */}
            {dataType === "numeric" && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Lower Limit{" "}
                    <span className="text-gray-400">(opt)</span>
                  </label>
                  <input
                    type="number"
                    step="any"
                    {...register("lower_limit")}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Upper Limit{" "}
                    <span className="text-gray-400">(opt)</span>
                  </label>
                  <input
                    type="number"
                    step="any"
                    {...register("upper_limit")}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
            )}

            {/* Enum values — only show for enum type */}
            {dataType === "enum" && (
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Enum Values{" "}
                  <span className="text-gray-400">
                    (comma-separated)
                  </span>
                </label>
                <input
                  {...register("enum_values")}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="pass,fail,rework"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Description{" "}
                <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                {...register("description")}
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
