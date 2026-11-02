/**
 * Find Storage Location dialog — same search/select behaviour as the
 * inventory client's location search (filter by code, name and type,
 * then pick one row with a radio button).
 */

import { useState } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { useStorageLocations } from "../hooks/useInventory";
import { LOCATION_TYPES, type LocationType, type StorageLocation } from "../types";

const TYPE_LABELS: Record<LocationType, string> = {
  receiving: "Receiving",
  storage: "Storage",
  rip: "Raw-in-Process",
  staging: "Staging",
  shipping: "Shipping",
};

interface Props {
  open: boolean;
  onClose: () => void;
  onSelect: (location: StorageLocation) => void;
}

const headerCell = "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500";

export default function LocationSearchDialog({ open, onClose, onSelect }: Props) {
  const { data } = useStorageLocations();
  const locations = data?.data ?? [];

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [results, setResults] = useState<StorageLocation[] | null>(null);
  const [selectedId, setSelectedId] = useState("");

  const find = (event: React.FormEvent) => {
    event.preventDefault();
    event.stopPropagation();
    const codeQuery = code.trim().toLowerCase();
    const nameQuery = name.trim().toLowerCase();
    setResults(
      locations.filter(
        (l) =>
          (!type || l.location_type === type) &&
          l.code.toLowerCase().includes(codeQuery) &&
          l.name.toLowerCase().includes(nameQuery),
      ),
    );
    setSelectedId("");
  };

  const clear = () => {
    setCode("");
    setName("");
    setType("");
    setResults(null);
    setSelectedId("");
  };

  const done = () => {
    const chosen = locations.find((l) => l.id === selectedId);
    if (!chosen) return;
    onSelect(chosen);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} className="relative z-[70]">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center overflow-auto p-4">
        <DialogPanel className="w-full max-w-5xl rounded-lg bg-white p-6 shadow-xl">
          <DialogTitle className="mb-4 text-lg font-semibold text-gray-900">
            Find Storage Location
          </DialogTitle>
          <form onSubmit={find} className="flex flex-col items-end gap-3 sm:flex-row">
            <div className="w-full flex-1">
              <label htmlFor="location-code-filter" className="mb-1 block text-sm font-medium text-gray-700">Code</label>
              <input
                id="location-code-filter"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="w-full flex-1">
              <label htmlFor="location-name-filter" className="mb-1 block text-sm font-medium text-gray-700">Name</label>
              <input
                id="location-name-filter"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="w-full sm:w-56">
              <label htmlFor="location-type-filter" className="mb-1 block text-sm font-medium text-gray-700">Type</label>
              <select
                id="location-type-filter"
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">All types</option>
                {LOCATION_TYPES.map((t) => (
                  <option key={t} value={t}>{TYPE_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                onClick={clear}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Clear
              </button>
              <button
                type="submit"
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
              >
                Find
              </button>
            </div>
          </form>

          {results !== null && (
            <div className="mt-5 max-h-[55vh] overflow-auto rounded-md border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="sticky top-0 bg-gray-50">
                  <tr>
                    <th scope="col" className={headerCell}>Select</th>
                    <th scope="col" className={headerCell}>Code</th>
                    <th scope="col" className={headerCell}>Name</th>
                    <th scope="col" className={headerCell}>Type</th>
                    <th scope="col" className={headerCell}>Aisle</th>
                    <th scope="col" className={headerCell}>Bay</th>
                    <th scope="col" className={headerCell}>Tier</th>
                    <th scope="col" className={`${headerCell} text-right`}>Capacity</th>
                    <th scope="col" className={headerCell}>Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {results.map((l) => (
                    <tr
                      key={l.id}
                      onClick={() => setSelectedId(l.id)}
                      className={`cursor-pointer ${selectedId === l.id ? "bg-indigo-50" : "hover:bg-gray-50"}`}
                    >
                      <td className="px-4 py-2.5">
                        <input
                          type="radio"
                          name="selected-location"
                          aria-label={`Select ${l.code}`}
                          checked={selectedId === l.id}
                          onChange={() => setSelectedId(l.id)}
                          className="text-indigo-600 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-4 py-2.5 text-sm font-medium text-gray-900">{l.code}</td>
                      <td className="px-4 py-2.5 text-sm text-gray-700">{l.name}</td>
                      <td className="px-4 py-2.5 text-sm text-gray-700">{TYPE_LABELS[l.location_type] ?? l.location_type}</td>
                      <td className="px-4 py-2.5 text-sm text-gray-600">{l.aisle ?? "—"}</td>
                      <td className="px-4 py-2.5 text-sm text-gray-600">{l.bay ?? "—"}</td>
                      <td className="px-4 py-2.5 text-sm text-gray-600">{l.tier ?? "—"}</td>
                      <td className="px-4 py-2.5 text-right text-sm font-mono text-gray-600">
                        {l.capacity === null
                          ? "—"
                          : `${l.capacity.toLocaleString()}${l.capacity_uom_symbol ? ` ${l.capacity_uom_symbol}` : ""}`}
                      </td>
                      <td className="px-4 py-2.5 text-sm text-gray-700">{l.is_active ? "Active" : "Inactive"}</td>
                    </tr>
                  ))}
                  {results.length === 0 && (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-400">
                        No locations found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-5">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={done}
              disabled={!selectedId}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Done
            </button>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
