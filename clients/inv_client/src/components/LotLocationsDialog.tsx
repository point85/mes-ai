import { useEffect, useState, Fragment } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { Dialog, Transition } from "@headlessui/react";
import { fetchInventoryBalances, fetchStorageLocations } from "../api";
import type { MaterialLot, InventoryBalance } from "../types";

interface Props {
  lot: MaterialLot | null;
  uomSymbol: string | null;
  open: boolean;
  onClose: () => void;
}

export function LotLocationsDialog({ lot, uomSymbol, open, onClose }: Props) {
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [locationCodes, setLocationCodes] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !lot) return;
    let cancelled = false;
    setBalances([]);
    setError(null);
    setLoading(true);
    Promise.all([fetchInventoryBalances({ material_lot_id: lot.id }), fetchStorageLocations()])
      .then(([bals, locs]) => {
        if (cancelled) return;
        setLocationCodes(new Map(locs.map((loc) => [loc.id, loc.code])));
        setBalances(bals.filter((b) => b.quantity_on_hand > 0));
      })
      .catch((e) => {
        if (cancelled) return;
        setError("Failed to load storage locations");
        console.error(e);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, lot]);

  return (
    <Transition appear show={open} as={Dialog} onClose={onClose}>
      <Dialog.Panel className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0 scale-95" enterTo="opacity-100 scale-100" leave="ease-in duration-200" leaveFrom="opacity-100 scale-100" leaveTo="opacity-0 scale-95">
          <Dialog.Panel className="w-full max-w-lg bg-white rounded-lg shadow-xl p-6">
            <Dialog.Title className="text-lg font-semibold text-gray-900 mb-4">Storage Locations: {lot?.lot_number}</Dialog.Title>
            {loading ? (
              <div className="p-8 text-center text-gray-500"><ArrowPathIcon className="mx-auto h-8 w-8 animate-spin text-indigo-600" /><p className="mt-2">Loading locations...</p></div>
            ) : error ? (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
            ) : balances.length === 0 ? (
              <p className="py-8 text-center text-sm text-gray-500">This lot has no inventory assigned to a storage location.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50"><tr><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th><th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">On Hand</th></tr></thead>
                  <tbody className="divide-y divide-gray-200">{balances.map((balance) => <tr key={balance.id}><td className="px-4 py-3 text-sm text-gray-900">{locationCodes.get(balance.location_id) ?? balance.location_id}</td><td className="px-4 py-3 text-sm text-right font-mono">{balance.quantity_on_hand.toLocaleString()}{uomSymbol ? ` ${uomSymbol}` : ""}</td></tr>)}</tbody>
                </table>
              </div>
            )}
            <div className="flex justify-end pt-5"><button type="button" onClick={onClose} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Close</button></div>
          </Dialog.Panel>
        </Transition.Child>
      </Dialog.Panel>
    </Transition>
  );
}
