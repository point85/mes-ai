/**
 * UoM Create / Edit dialog — modal form with Zod validation.
 *
 * Supports four UoM classes:
 *   scalar   — type + multiplier + offset
 *   quotient — left (numerator) type+unit / right (denominator) type+unit
 *   product  — left type+unit × right type+unit
 *   power    — base type+unit ^ exponent
 */

import { useEffect, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateUoM, useUpdateUoM, useUoMs } from "../../hooks/useUoM";
import type { UoM, UoMClass } from "../../types";
import { UOM_TYPES, UOM_CLASSES } from "../../types";

const CLASS_LABELS: Record<UoMClass, string> = {
  scalar: "Scalar",
  quotient: "Quotient (÷)",
  product: "Product (×)",
  power: "Power (^)",
};

const TYPE_LABELS: Record<string, string> = {
  mass: "Mass",
  length: "Length",
  time: "Time",
  temperature: "Temperature",
  other: "Other",
};

const uomSchema = z
  .object({
    symbol: z
      .string()
      .min(1, "Symbol is required")
      .max(20)
      .refine((s) => !s.includes(" "), "Symbol must not contain spaces"),
    name: z.string().min(1, "Name is required").max(100),
    description: z.string().nullable().optional(),
    uom_type: z.string().min(1, "Type is required"),
    uom_class: z.enum(["scalar", "quotient", "product", "power"]),
    multiplier: z.coerce.number().positive("Must be > 0"),
    offset: z.coerce.number(),
    left_uom_symbol: z.string().nullable().optional(),
    right_uom_symbol: z.string().nullable().optional(),
    exponent: z.coerce.number().int().min(2).nullable().optional(),
  })
  .superRefine((data, ctx) => {
    const cls = data.uom_class;
    if (cls === "quotient" || cls === "product") {
      if (!data.left_uom_symbol)
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Required", path: ["left_uom_symbol"] });
      if (!data.right_uom_symbol)
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Required", path: ["right_uom_symbol"] });
    }
    if (cls === "power") {
      if (!data.left_uom_symbol)
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Required", path: ["left_uom_symbol"] });
      if (!data.exponent)
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Required (≥ 2)", path: ["exponent"] });
    }
  });

type UoMFormData = z.infer<typeof uomSchema>;

interface Props {
  uom: UoM | null; // null = create mode
  onClose: () => void;
}

// A type+unit pair selector used for composite classes
function ComponentSelector({
  label,
  typeName,
  symbolName,
  scalarUoms,
  register,
  watch,
  errors,
}: {
  label: string;
  typeName: "left_uom_type_filter" | "right_uom_type_filter";
  symbolName: "left_uom_symbol" | "right_uom_symbol";
  scalarUoms: UoM[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  watch: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  errors: any;
}) {
  const selectedType = watch(typeName) as string;
  const filteredUoms = selectedType
    ? scalarUoms.filter((u) => u.uom_type === selectedType)
    : scalarUoms;

  return (
    <div className="space-y-2 rounded-md border border-gray-200 p-3 bg-gray-50">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
        <select
          {...register(typeName)}
          className="block w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">Any type</option>
          {UOM_TYPES.map((t) => (
            <option key={t} value={t}>{TYPE_LABELS[t]}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Unit</label>
        <select
          {...register(symbolName)}
          className="block w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">Select unit…</option>
          {filteredUoms.map((u) => (
            <option key={u.symbol} value={u.symbol}>
              {u.symbol} — {u.name}
            </option>
          ))}
        </select>
        {errors[symbolName] && (
          <p className="mt-1 text-xs text-red-600">{errors[symbolName].message}</p>
        )}
      </div>
    </div>
  );
}

export default function UoMFormDialog({ uom, onClose }: Props) {
  const isEdit = !!uom;
  const createMut = useCreateUoM();
  const updateMut = useUpdateUoM();
  const { data: allUoMs } = useUoMs();

  // Only scalar UoMs can be components of composite ones
  const scalarUoms = useMemo(
    () => (allUoMs?.data ?? []).filter((u) => u.uom_class === "scalar"),
    [allUoMs],
  );

  const {
    register,
    handleSubmit,
    reset,
    watch,
    control,
    formState: { errors, isSubmitting },
  } = useForm<UoMFormData & { left_uom_type_filter: string; right_uom_type_filter: string }>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(uomSchema) as any,
    defaultValues: {
      symbol: "",
      name: "",
      description: "",
      uom_type: "",
      uom_class: "scalar",
      multiplier: 1,
      offset: 0,
      left_uom_symbol: null,
      right_uom_symbol: null,
      exponent: null,
      left_uom_type_filter: "",
      right_uom_type_filter: "",
    },
  });

  const watchedClass = watch("uom_class") as UoMClass;
  const isScalar = watchedClass === "scalar";
  const isComposite = !isScalar;

  useEffect(() => {
    if (uom) {
      reset({
        symbol: uom.symbol,
        name: uom.name,
        description: uom.description ?? "",
        uom_type: uom.uom_type,
        uom_class: uom.uom_class,
        multiplier: uom.multiplier,
        offset: uom.offset,
        left_uom_symbol: uom.left_uom_symbol ?? null,
        right_uom_symbol: uom.right_uom_symbol ?? null,
        exponent: uom.exponent ?? null,
        left_uom_type_filter: uom.left_uom_type ?? "",
        right_uom_type_filter: uom.right_uom_type ?? "",
      });
    }
  }, [uom, reset]);

  const onSubmit = async (data: UoMFormData & { left_uom_type_filter: string; right_uom_type_filter: string }) => {
    try {
      const { left_uom_type_filter: _l, right_uom_type_filter: _r, ...rest } = data;
      const payload = {
        ...rest,
        left_uom_symbol: isComposite ? rest.left_uom_symbol : null,
        right_uom_symbol: (watchedClass === "quotient" || watchedClass === "product") ? rest.right_uom_symbol : null,
        exponent: watchedClass === "power" ? rest.exponent : null,
      };
      if (isEdit) {
        await updateMut.mutateAsync({ id: uom!.id, ...payload });
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
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

      {/* Panel */}
      <div className="fixed inset-0 flex items-center justify-center p-4 overflow-y-auto">
        <DialogPanel className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl my-4">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Unit" : "New Unit of Measure"}
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
              {(mutError as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                "An error occurred"}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Symbol */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Symbol</label>
              <input
                {...register("symbol")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="kg, lb, m/s, m³ …"
              />
              {errors.symbol && (
                <p className="mt-1 text-xs text-red-600">{errors.symbol.message}</p>
              )}
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                {...register("name")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="kilogram, meters per second, cubic meter …"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
              )}
            </div>

            {/* Class radio buttons */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Class</label>
              <Controller
                name="uom_class"
                control={control}
                render={({ field }) => (
                  <div className="flex flex-wrap gap-3">
                    {UOM_CLASSES.map((cls) => (
                      <label key={cls} className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="radio"
                          value={cls}
                          checked={field.value === cls}
                          onChange={() => field.onChange(cls)}
                          className="accent-indigo-600"
                        />
                        <span className="text-sm text-gray-700">{CLASS_LABELS[cls]}</span>
                      </label>
                    ))}
                  </div>
                )}
              />
            </div>

            {/* Scalar fields: type + multiplier + offset */}
            {isScalar && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Type</label>
                  <select
                    {...register("uom_type")}
                    className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="">Select type…</option>
                    {UOM_TYPES.map((t) => (
                      <option key={t} value={t}>{TYPE_LABELS[t]}</option>
                    ))}
                  </select>
                  {errors.uom_type && (
                    <p className="mt-1 text-xs text-red-600">{errors.uom_type.message}</p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Multiplier <span className="text-gray-400 text-xs">(a)</span>
                    </label>
                    <input
                      type="number"
                      step="any"
                      {...register("multiplier")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                    <p className="mt-0.5 text-xs text-gray-400">base = value × a + b</p>
                    {errors.multiplier && (
                      <p className="mt-1 text-xs text-red-600">{errors.multiplier.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Offset <span className="text-gray-400 text-xs">(b)</span>
                    </label>
                    <input
                      type="number"
                      step="any"
                      {...register("offset")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                    {errors.offset && (
                      <p className="mt-1 text-xs text-red-600">{errors.offset.message}</p>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* Quotient fields: left / right */}
            {watchedClass === "quotient" && (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 font-medium">
                  Result = <em>left</em> ÷ <em>right</em> (e.g. kg ÷ s = kg/s)
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <ComponentSelector
                    label="Numerator (left)"
                    typeName="left_uom_type_filter"
                    symbolName="left_uom_symbol"
                    scalarUoms={scalarUoms}
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                  <ComponentSelector
                    label="Denominator (right)"
                    typeName="right_uom_type_filter"
                    symbolName="right_uom_symbol"
                    scalarUoms={scalarUoms}
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                </div>
              </div>
            )}

            {/* Product fields: left × right */}
            {watchedClass === "product" && (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 font-medium">
                  Result = <em>left</em> × <em>right</em> (e.g. kg × m)
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <ComponentSelector
                    label="First factor (left)"
                    typeName="left_uom_type_filter"
                    symbolName="left_uom_symbol"
                    scalarUoms={scalarUoms}
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                  <ComponentSelector
                    label="Second factor (right)"
                    typeName="right_uom_type_filter"
                    symbolName="right_uom_symbol"
                    scalarUoms={scalarUoms}
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                </div>
              </div>
            )}

            {/* Power fields: base ^ exponent */}
            {watchedClass === "power" && (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 font-medium">
                  Result = <em>base</em> ^ <em>exponent</em> (e.g. m ^ 3 = m³)
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <ComponentSelector
                    label="Base unit"
                    typeName="left_uom_type_filter"
                    symbolName="left_uom_symbol"
                    scalarUoms={scalarUoms}
                    register={register}
                    watch={watch}
                    errors={errors}
                  />
                  <div className="space-y-2 rounded-md border border-gray-200 p-3 bg-gray-50">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Exponent</p>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Integer ≥ 2</label>
                      <input
                        type="number"
                        min={2}
                        step={1}
                        {...register("exponent")}
                        className="block w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                        placeholder="2, 3, …"
                      />
                      {errors.exponent && (
                        <p className="mt-1 text-xs text-red-600">{errors.exponent.message}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                {...register("description")}
                rows={2}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
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
