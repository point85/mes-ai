/**
 * Location Form Dialog — create/edit a storage location in a modal dialog.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import {
  useCreateStorageLocation,
  useUpdateStorageLocation,
} from "../../hooks/useInventory";
import { useSites } from "../../hooks/usePhysicalModel";
import type { StorageLocation, StorageLocationCreate } from "../../types";
import { LOCATION_TYPES } from "../../types/inventory";

const TYPE_LABELS: Record<string, string> = {
  receiving: "Receiving",
  storage: "Storage",
  rip: "Raw-in-Process",
  staging: "Staging",
  shipping: "Shipping",
};

interface Props {
  location: StorageLocation | null; // null = create mode
  onClose: () => void;
}

export default function LocationFormDialog({ location, onClose }: Props) {
  const createMut = useCreateStorageLocation();
  const updateMut = useUpdateStorageLocation();
  const { data: sitesData } = useSites();
  const sites = sitesData?.data ?? [];

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<StorageLocationCreate>({
    defaultValues: {
      name: location?.name ?? "",
      code: location?.code ?? "",
      description: location?.description ?? "",
      location_type: location?.location_type ?? "storage",
      aisle: location?.aisle ?? "",
      bay: location?.bay ?? "",
      tier: location?.tier ?? "",
      site_id: location?.site_id ?? undefined,
      capacity: location?.capacity ?? undefined,
    },
  });

  useEffect(() => {
    reset({
      name: location?.name ?? "",
      code: location?.code ?? "",
      description: location?.description ?? "",
      location_type: location?.location_type ?? "storage",
      aisle: location?.aisle ?? "",
      bay: location?.bay ?? "",
      tier: location?.tier ?? "",
      site_id: location?.site_id ?? undefined,
      capacity: location?.capacity ?? undefined,
    });
  }, [location, reset]);

  const onSubmit = async (data: StorageLocationCreate) => {
    const payload = {
      ...data,
      description: data.description || null,
      aisle: data.aisle || null,
      bay: data.bay || null,
      tier: data.tier || null,
      site_id: data.site_id || null,
      capacity: data.capacity ? Number(data.capacity) : null,
    };
    if (location) {
      await updateMut.mutateAsync({ id: location.id, ...payload });
    } else {
      await createMut.mutateAsync(payload);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">
          {location ? "Edit Storage Location" : "New Storage Location"}
        </h2>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4">
          {/* Code & Name row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Code
              </label>
              <input
                {...register("code", {
                  required: "Code is required",
                  pattern: {
                    value: /^\S+$/,
                    message: "Code must not contain spaces",
                  },
                })}
                maxLength={50}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
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
                {...register("name", { required: "Name is required" })}
                maxLength={255}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.name.message}
                </p>
              )}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Description
            </label>
            <textarea
              {...register("description")}
              rows={2}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Type & Site row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Location Type
              </label>
              <select
                {...register("location_type", {
                  required: "Type is required",
                })}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                {LOCATION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Site
              </label>
              <select
                {...register("site_id")}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">— None —</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code} — {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Aisle / Bay / Tier row */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Aisle
              </label>
              <input
                {...register("aisle")}
                maxLength={20}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Bay
              </label>
              <input
                {...register("bay")}
                maxLength={20}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Tier
              </label>
              <input
                {...register("tier")}
                maxLength={20}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Capacity */}
          <div className="w-1/3">
            <label className="block text-sm font-medium text-gray-700">
              Capacity
            </label>
            <input
              {...register("capacity", {
                validate: (v) =>
                  !v || Number(v) > 0 || "Capacity must be positive",
              })}
              type="number"
              step="any"
              min="0"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
            {errors.capacity && (
              <p className="mt-1 text-xs text-red-600">
                {errors.capacity.message}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              {location ? "Save" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
