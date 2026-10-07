import { useEffect, useState, Fragment } from "react";
import { Dialog, Transition } from "@headlessui/react";
import type { Material } from "../types";

interface Props {
  open: boolean;
  refreshMaterials: () => Promise<Material[]>;
  onClose: () => void;
  onSelect: (materialId: string) => void;
  onClear?: () => void;
}

export function MaterialSearchDialog({ open, refreshMaterials, onClose, onSelect, onClear }: Props) {
  const [codeQuery, setCodeQuery] = useState("");
  const [typeQuery, setTypeQuery] = useState("");
  const [results, setResults] = useState<Material[] | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setCodeQuery("");
    setTypeQuery("");
    setResults(null);
    setSelectedId("");
    setSearchError(null);
  }, [open]);

  const find = async (event: React.FormEvent) => {
    event.preventDefault();
    const code = codeQuery.trim().toLowerCase();
    setSearching(true);
    setSearchError(null);
    setSelectedId("");
    try {
      const latestMaterials = await refreshMaterials();
      setResults(latestMaterials.filter((material) =>
        material.code.toLowerCase().includes(code) &&
        (!typeQuery || material.material_type === typeQuery),
      ));
    } catch (error) {
      console.error(error);
      setSearchError("Failed to refresh materials. Please try again.");
      setResults(null);
    } finally {
      setSearching(false);
    }
  };

  const clear = () => {
    setCodeQuery("");
    setTypeQuery("");
    setResults(null);
    setSelectedId("");
    setSearchError(null);
    onClear?.();
  };

  const done = () => {
    if (!selectedId) return;
    onSelect(selectedId);
    onClose();
  };

  const headerClass = "px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500";

  return (
    <Transition appear show={open} as={Dialog} onClose={onClose}>
      <Dialog.Panel className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
        <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0 scale-95" enterTo="opacity-100 scale-100" leave="ease-in duration-200" leaveFrom="opacity-100 scale-100" leaveTo="opacity-0 scale-95">
          <Dialog.Panel className="w-full max-w-4xl rounded-lg bg-white p-6 shadow-xl">
            <Dialog.Title className="mb-4 text-lg font-semibold text-gray-900">Find Material</Dialog.Title>
            <form onSubmit={find} className="flex flex-col items-end gap-3 sm:flex-row">
              <div className="w-full flex-1">
                <label htmlFor="material-code-query" className="mb-1 block text-sm font-medium text-gray-700">Code</label>
                <input id="material-code-query" type="text" value={codeQuery} onChange={(event) => setCodeQuery(event.target.value)} className="input-field" />
              </div>
              <div className="w-full sm:w-56">
                <label htmlFor="material-type-query" className="mb-1 block text-sm font-medium text-gray-700">Material Type</label>
                <select id="material-type-query" value={typeQuery} onChange={(event) => setTypeQuery(event.target.value)} className="input-field">
                  <option value="">All types</option>
                  <option value="raw">Raw</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="finished">Finished</option>
                </select>
              </div>
              <div className="flex shrink-0 gap-2">
                <button type="button" onClick={clear} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Clear</button>
                <button type="submit" disabled={searching} className="btn-primary disabled:cursor-not-allowed disabled:opacity-50">{searching ? "Searching..." : "Find"}</button>
              </div>
            </form>

            {searchError && <div role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{searchError}</div>}

            {results !== null && (
              <div className="mt-5 max-h-[55vh] overflow-auto rounded-md border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="sticky top-0 bg-gray-50">
                    <tr>
                      <th scope="col" className={`${headerClass} text-left`}>Select</th>
                      <th scope="col" className={`${headerClass} text-left`}>Code</th>
                      <th scope="col" className={`${headerClass} text-left`}>Name</th>
                      <th scope="col" className={`${headerClass} text-left`}>Type</th>
                      <th scope="col" className={`${headerClass} text-left`}>UoM</th>
                      <th scope="col" className={`${headerClass} text-right`}>Shelf Life (days)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {results.map((material) => (
                      <tr key={material.id} onClick={() => setSelectedId(material.id)} className={`cursor-pointer ${selectedId === material.id ? "bg-indigo-50" : "hover:bg-gray-50"}`}>
                        <td className="px-4 py-2.5">
                          <input type="radio" name="selected-material" aria-label={`Select ${material.code}`} checked={selectedId === material.id} onChange={() => setSelectedId(material.id)} className="text-indigo-600 focus:ring-indigo-500" />
                        </td>
                        <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">{material.code}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{material.name}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{material.material_type}</td>
                        <td className="px-4 py-2.5 text-sm font-mono text-gray-600">{material.uom_symbol ?? "—"}</td>
                        <td className="px-4 py-2.5 text-right text-sm font-mono text-gray-600">{material.shelf_life_days ?? "—"}</td>
                      </tr>
                    ))}
                    {results.length === 0 && (
                      <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">No materials found.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-5">
              <button type="button" onClick={onClose} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
              <button type="button" onClick={done} disabled={!selectedId} className="btn-primary disabled:cursor-not-allowed disabled:opacity-50">Done</button>
            </div>
          </Dialog.Panel>
        </Transition.Child>
      </Dialog.Panel>
    </Transition>
  );
}
