/**
 * Site Create / Edit dialog — modal form with Zod validation.
 */

import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCreateSite, useUpdateSite } from "../../hooks/usePhysicalModel";
import { useWorkSchedules } from "../../hooks/useWorkSchedule";
import type { Site } from "../../types";

const siteSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  code: z
    .string()
    .min(1, "Code is required")
    .max(50)
    .refine((s) => !s.includes(" "), "Code must not contain spaces"),
  description: z.string().nullable().optional(),
  timezone: z.string().nullable().optional(),
  address: z.string().nullable().optional(),
  work_schedule_id: z.string().uuid().nullable().optional(),
});

type SiteFormData = z.infer<typeof siteSchema>;

interface Props {
  site: Site | null;
  onClose: () => void;
}

export default function SiteFormDialog({ site, onClose }: Props) {
  const isEdit = !!site;
  const createMut = useCreateSite();
  const updateMut = useUpdateSite();
  const { data: schedulesData } = useWorkSchedules();
  const tzByRegion = useMemo(() => {
    const all = Intl.supportedValuesOf("timeZone");
    const map: Record<string, string[]> = {};
    for (const tz of all) {
      const slash = tz.indexOf("/");
      const region = slash > 0 ? tz.substring(0, slash) : "Other";
      (map[region] ??= []).push(tz);
    }
    return map;
  }, []);

  const regions = useMemo(() => Object.keys(tzByRegion).sort(), [tzByRegion]);
  const [selectedRegion, setSelectedRegion] = useState<string>("");
  const filteredTimezones = selectedRegion ? (tzByRegion[selectedRegion] ?? []) : [];

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SiteFormData>({
    resolver: zodResolver(siteSchema),
    defaultValues: {
      name: "",
      code: "",
      description: "",
      timezone: "",
      address: "",
      work_schedule_id: null,
    },
  });

  const currentTimezone = watch("timezone");

  useEffect(() => {
    if (site) {
      reset({
        name: site.name,
        code: site.code,
        description: site.description ?? "",
        timezone: site.timezone ?? "",
        address: site.address ?? "",
        work_schedule_id: site.work_schedule_id ?? null,
      });
      // Pre-select region from existing timezone
      if (site.timezone) {
        const slash = site.timezone.indexOf("/");
        if (slash > 0) setSelectedRegion(site.timezone.substring(0, slash));
      }
    }
  }, [site, reset]);

  const onSubmit = async (data: SiteFormData) => {
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: site!.id, ...data });
      } else {
        await createMut.mutateAsync(data);
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
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {isEdit ? "Edit Site" : "New Site"}
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
                Code
              </label>
              <input
                {...register("code")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="SITE-01"
              />
              {errors.code && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.code.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                {...register("name")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="Main Manufacturing Plant"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.name.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Timezone{" "}
                <span className="text-gray-400">(optional)</span>
              </label>
              <div className="mt-1 grid grid-cols-2 gap-2">
                <select
                  value={selectedRegion}
                  onChange={(e) => {
                    setSelectedRegion(e.target.value);
                    setValue("timezone", "");
                  }}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">— Region —</option>
                  {regions.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <select
                  {...register("timezone")}
                  disabled={!selectedRegion}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-100 disabled:text-gray-400"
                >
                  <option value="">— Timezone —</option>
                  {filteredTimezones.map((tz) => (
                    <option key={tz} value={tz}>{tz.substring(tz.indexOf("/") + 1).replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Address{" "}
                <span className="text-gray-400">(optional)</span>
              </label>
              <input
                {...register("address")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                placeholder="123 Industrial Ave, …"
              />
            </div>

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

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Work Schedule <span className="text-gray-400">(optional)</span>
              </label>
              <select
                {...register("work_schedule_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— None —</option>
                {schedulesData?.data?.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
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
