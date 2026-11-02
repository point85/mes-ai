import { useEffect, useRef, useState } from "react";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
  createMaterialLot,
  fetchMaterials,
  fetchStorageLocations,
  receiveInventory,
} from "../api/runtime";
import type { Material, StorageLocation } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onReceived: (lotNumber: string, materialName: string) => void | Promise<void>;
}

const LOCATION_TYPE_LABELS: Record<string, string> = {
  receiving: "Receiving",
  storage: "Storage",
  rip: "Raw-in-Process",
  staging: "Staging",
  shipping: "Shipping",
};

const HEADER = "px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500";
const SEARCH_BTN = "inline-flex shrink-0 items-center justify-center rounded-md border border-gray-300 bg-white px-3 text-gray-700 hover:bg-gray-50";
const CANCEL_BTN = "rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50";

function extractError(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const resp = (err as { response?: { data?: { message?: string; detail?: unknown; error?: { message?: string } } } }).response;
    if (resp?.data?.error?.message) return resp.data.error.message;
    if (resp?.data?.message) return resp.data.message;
    if (resp?.data?.detail) return typeof resp.data.detail === "string" ? resp.data.detail : JSON.stringify(resp.data.detail);
  }
  return err instanceof Error ? err.message : "Operation failed";
}

export default function ReceiveDialog({ open, onClose, onReceived }: Props) {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [lotNumber, setLotNumber] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [quantity, setQuantity] = useState<number | "">("");
  const [receivedDate, setReceivedDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [supplier, setSupplier] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // A lot created by an earlier attempt whose receive step failed is reused instead of duplicated.
  const pendingLotId = useRef<string | null>(null);

  const [materialSearchOpen, setMaterialSearchOpen] = useState(false);
  const [materialCodeQuery, setMaterialCodeQuery] = useState("");
  const [materialTypeQuery, setMaterialTypeQuery] = useState("");
  const [materialResults, setMaterialResults] = useState<Material[] | null>(null);
  const [materialPick, setMaterialPick] = useState("");
  const [materialSearching, setMaterialSearching] = useState(false);
  const [materialSearchError, setMaterialSearchError] = useState<string | null>(null);

  const [locationSearchOpen, setLocationSearchOpen] = useState(false);
  const [locationCodeFilter, setLocationCodeFilter] = useState("");
  const [locationNameFilter, setLocationNameFilter] = useState("");
  const [locationResults, setLocationResults] = useState<StorageLocation[] | null>(null);
  const [locationPick, setLocationPick] = useState("");

  useEffect(() => {
    if (!open) return;
    setLotNumber("");
    setMaterialId("");
    setLocationId("");
    setQuantity("");
    setReceivedDate("");
    setExpiryDate("");
    setSupplier("");
    setReason("");
    setError(null);
    pendingLotId.current = null;
    fetchMaterials().then(setMaterials).catch(() => setError("Failed to load materials."));
    fetchStorageLocations().then(setLocations).catch(() => setError("Failed to load storage locations."));
  }, [open]);

  const material = materials.find((m) => m.id === materialId);
  const isUnit = material?.tracking_method === "unit";
  const selectedLocation = locations.find((l) => l.id === locationId);

  const changeReceivedDate = (value: string) => {
    setReceivedDate(value);
    const shelfLifeDays = material?.shelf_life_days;
    if (value && shelfLifeDays) {
      const expiry = new Date(`${value}T00:00:00Z`);
      expiry.setUTCDate(expiry.getUTCDate() + shelfLifeDays);
      setExpiryDate(expiry.toISOString().slice(0, 10));
    }
  };

  const openMaterialSearch = () => {
    setMaterialCodeQuery("");
    setMaterialTypeQuery("");
    setMaterialResults(null);
    setMaterialPick("");
    setMaterialSearchError(null);
    setMaterialSearchOpen(true);
  };

  const findMaterials = async (event: React.FormEvent) => {
    event.preventDefault();
    const code = materialCodeQuery.trim().toLowerCase();
    setMaterialSearching(true);
    setMaterialSearchError(null);
    setMaterialPick("");
    try {
      const latest = await fetchMaterials();
      setMaterials(latest);
      setMaterialResults(latest.filter((m) =>
        m.code.toLowerCase().includes(code) && (!materialTypeQuery || m.material_type === materialTypeQuery),
      ));
    } catch {
      setMaterialSearchError("Failed to refresh materials. Please try again.");
      setMaterialResults(null);
    } finally {
      setMaterialSearching(false);
    }
  };

  const openLocationSearch = () => {
    setLocationCodeFilter("");
    setLocationNameFilter("");
    setLocationResults(null);
    setLocationPick("");
    setLocationSearchOpen(true);
  };

  const findLocations = (event: React.FormEvent) => {
    event.preventDefault();
    const code = locationCodeFilter.trim().toLowerCase();
    const name = locationNameFilter.trim().toLowerCase();
    setLocationResults(locations.filter((l) =>
      l.location_type === "receiving" &&
      l.code.toLowerCase().includes(code) &&
      l.name.toLowerCase().includes(name),
    ));
    setLocationPick("");
  };

  const canExecute = !!materialId && !!lotNumber.trim() && !!locationId;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (!pendingLotId.current) {
        const created = await createMaterialLot({
          material_id: materialId,
          lot_number: lotNumber.trim(),
          ...(isUnit ? {} : { quantity_on_hand: quantity === "" ? 0 : quantity }),
          received_date: receivedDate || null,
          expiry_date: expiryDate || null,
          supplier: supplier.trim() || null,
        });
        pendingLotId.current = created.id;
      }
      await receiveInventory({
        material_lot_id: pendingLotId.current,
        to_location_id: locationId,
        ...(isUnit || quantity === "" ? {} : { quantity }),
        ...(reason.trim() ? { reason: reason.trim() } : {}),
      });
      pendingLotId.current = null;
      await onReceived(lotNumber.trim(), material?.name ?? "");
      onClose();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} className="relative z-50">
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <DialogTitle className="mb-4 text-lg font-semibold text-gray-900">Receive</DialogTitle>
            {error && <div role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="receive-lot-number" className="mb-1 block text-sm font-medium text-gray-700">{isUnit ? "Serial Number" : "Lot Number"} *</label>
                <input id="receive-lot-number" type="text" value={lotNumber} onChange={(e) => { setLotNumber(e.target.value); pendingLotId.current = null; }} required className="input-field" />
              </div>
              <div>
                <label htmlFor="receive-material" className="mb-1 block text-sm font-medium text-gray-700">Material *</label>
                <div className="flex gap-2">
                  <input id="receive-material" type="text" value={material?.name ?? ""} placeholder="Select a material" readOnly className="input-field min-w-0 flex-1" />
                  <button type="button" onClick={openMaterialSearch} aria-label="Search materials" title="Search materials" className={SEARCH_BTN}>
                    <MagnifyingGlassIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="receive-location" className="mb-1 block text-sm font-medium text-gray-700">To Location *</label>
                <div className="flex gap-2">
                  <input id="receive-location" type="text" value={selectedLocation ? `${selectedLocation.code} - ${selectedLocation.name}` : ""} placeholder="Select a location" readOnly className="input-field min-w-0 flex-1" />
                  <button type="button" onClick={openLocationSearch} aria-label="Search to location" title="Search to location" className={SEARCH_BTN}>
                    <MagnifyingGlassIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
              {!isUnit && (
                <div className="flex items-end gap-3">
                  <div className="min-w-0 flex-1">
                    <label htmlFor="receive-quantity" className="mb-1 block text-sm font-medium text-gray-700">Quantity *</label>
                    <input id="receive-quantity" type="number" value={quantity} onChange={(e) => setQuantity(e.target.value === "" ? "" : Number(e.target.value))} required min="0.01" step="any" className="input-field" />
                  </div>
                  <div className="w-28 shrink-0">
                    <span className="mb-1 block text-sm font-medium text-gray-700">UoM</span>
                    <div aria-label="Unit of measure" className="input-field flex items-center bg-gray-50 text-gray-500">{material?.uom_symbol ?? "—"}</div>
                  </div>
                </div>
              )}
              <div>
                <label htmlFor="receive-received-date" className="mb-1 block text-sm font-medium text-gray-700">Received Date</label>
                <input id="receive-received-date" type="date" value={receivedDate} onChange={(e) => changeReceivedDate(e.target.value)} className="input-field" />
              </div>
              <div>
                <label htmlFor="receive-expiry-date" className="mb-1 block text-sm font-medium text-gray-700">Expiry Date</label>
                <input id="receive-expiry-date" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} className="input-field" />
              </div>
              <div>
                <label htmlFor="receive-supplier" className="mb-1 block text-sm font-medium text-gray-700">Supplier</label>
                <input id="receive-supplier" type="text" value={supplier} onChange={(e) => setSupplier(e.target.value)} className="input-field" />
              </div>
              <div>
                <label htmlFor="receive-reference" className="mb-1 block text-sm font-medium text-gray-700">Reference</label>
                <textarea id="receive-reference" value={reason} onChange={(e) => setReason(e.target.value)} rows={2} className="input-field" />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={onClose} className={CANCEL_BTN}>Cancel</button>
                <button type="submit" disabled={loading || !canExecute} className="btn-primary">{loading ? "Processing..." : "Execute"}</button>
              </div>
            </form>
          </DialogPanel>
        </div>
      </Dialog>

      <Dialog open={open && materialSearchOpen} onClose={() => setMaterialSearchOpen(false)} className="relative z-[60]">
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="w-full max-w-4xl rounded-lg bg-white p-6 shadow-xl">
            <DialogTitle className="mb-4 text-lg font-semibold text-gray-900">Find Material</DialogTitle>
            <form onSubmit={findMaterials} className="flex flex-col items-end gap-3 sm:flex-row">
              <div className="w-full flex-1">
                <label htmlFor="material-code-query" className="mb-1 block text-sm font-medium text-gray-700">Code</label>
                <input id="material-code-query" type="text" value={materialCodeQuery} onChange={(e) => setMaterialCodeQuery(e.target.value)} className="input-field" />
              </div>
              <div className="w-full sm:w-56">
                <label htmlFor="material-type-query" className="mb-1 block text-sm font-medium text-gray-700">Material Type</label>
                <select id="material-type-query" value={materialTypeQuery} onChange={(e) => setMaterialTypeQuery(e.target.value)} className="input-field">
                  <option value="">All types</option>
                  <option value="raw">Raw</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="finished">Finished</option>
                </select>
              </div>
              <div className="flex shrink-0 gap-2">
                <button type="button" onClick={() => { setMaterialCodeQuery(""); setMaterialTypeQuery(""); setMaterialResults(null); setMaterialPick(""); setMaterialSearchError(null); setMaterialId(""); pendingLotId.current = null; }} className={CANCEL_BTN}>Clear</button>
                <button type="submit" disabled={materialSearching} className="btn-primary">{materialSearching ? "Searching..." : "Find"}</button>
              </div>
            </form>
            {materialSearchError && <div role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{materialSearchError}</div>}
            {materialResults !== null && (
              <div className="mt-5 max-h-[55vh] overflow-auto rounded-md border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="sticky top-0 bg-gray-50">
                    <tr>
                      <th scope="col" className={`${HEADER} text-left`}>Select</th>
                      <th scope="col" className={`${HEADER} text-left`}>Code</th>
                      <th scope="col" className={`${HEADER} text-left`}>Name</th>
                      <th scope="col" className={`${HEADER} text-left`}>Type</th>
                      <th scope="col" className={`${HEADER} text-left`}>UoM</th>
                      <th scope="col" className={`${HEADER} text-right`}>Shelf Life (days)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {materialResults.map((m) => (
                      <tr key={m.id} onClick={() => setMaterialPick(m.id)} className={`cursor-pointer ${materialPick === m.id ? "bg-indigo-50" : "hover:bg-gray-50"}`}>
                        <td className="px-4 py-2.5">
                          <input type="radio" name="selected-material" aria-label={`Select ${m.code}`} checked={materialPick === m.id} onChange={() => setMaterialPick(m.id)} className="text-indigo-600 focus:ring-indigo-500" />
                        </td>
                        <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">{m.code}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{m.name}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{m.material_type}</td>
                        <td className="px-4 py-2.5 text-sm font-mono text-gray-600">{m.uom_symbol ?? "—"}</td>
                        <td className="px-4 py-2.5 text-right text-sm font-mono text-gray-600">{m.shelf_life_days ?? "—"}</td>
                      </tr>
                    ))}
                    {materialResults.length === 0 && (
                      <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">No materials found.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex justify-end gap-3 pt-5">
              <button type="button" onClick={() => setMaterialSearchOpen(false)} className={CANCEL_BTN}>Cancel</button>
              <button
                type="button"
                disabled={!materialPick}
                onClick={() => { setMaterialId(materialPick); pendingLotId.current = null; setMaterialSearchOpen(false); }}
                className="btn-primary"
              >
                Done
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>

      <Dialog open={open && locationSearchOpen} onClose={() => setLocationSearchOpen(false)} className="relative z-[70]">
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="w-full max-w-5xl rounded-lg bg-white p-6 shadow-xl">
            <DialogTitle className="mb-4 text-lg font-semibold text-gray-900">Find Storage Location</DialogTitle>
            <form onSubmit={findLocations} className="flex flex-col items-end gap-3 sm:flex-row">
              <div className="w-full flex-1">
                <label htmlFor="location-code-filter" className="mb-1 block text-sm font-medium text-gray-700">Code</label>
                <input id="location-code-filter" type="text" value={locationCodeFilter} onChange={(e) => setLocationCodeFilter(e.target.value)} className="input-field" />
              </div>
              <div className="w-full flex-1">
                <label htmlFor="location-name-filter" className="mb-1 block text-sm font-medium text-gray-700">Name</label>
                <input id="location-name-filter" type="text" value={locationNameFilter} onChange={(e) => setLocationNameFilter(e.target.value)} className="input-field" />
              </div>
              <div className="flex shrink-0 gap-2">
                <button type="button" onClick={() => { setLocationCodeFilter(""); setLocationNameFilter(""); setLocationResults(null); setLocationPick(""); setLocationId(""); }} className={CANCEL_BTN}>Clear</button>
                <button type="submit" className="btn-primary">Find</button>
              </div>
            </form>
            {locationResults !== null && (
              <div className="mt-5 max-h-[55vh] overflow-auto rounded-md border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="sticky top-0 bg-gray-50">
                    <tr>
                      <th scope="col" className={`${HEADER} text-left`}>Select</th>
                      <th scope="col" className={`${HEADER} text-left`}>Code</th>
                      <th scope="col" className={`${HEADER} text-left`}>Name</th>
                      <th scope="col" className={`${HEADER} text-left`}>Type</th>
                      <th scope="col" className={`${HEADER} text-left`}>Aisle</th>
                      <th scope="col" className={`${HEADER} text-left`}>Bay</th>
                      <th scope="col" className={`${HEADER} text-left`}>Tier</th>
                      <th scope="col" className={`${HEADER} text-right`}>Capacity</th>
                      <th scope="col" className={`${HEADER} text-left`}>Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {locationResults.map((l) => (
                      <tr key={l.id} onClick={() => setLocationPick(l.id)} className={`cursor-pointer ${locationPick === l.id ? "bg-indigo-50" : "hover:bg-gray-50"}`}>
                        <td className="px-4 py-2.5"><input type="radio" name="selected-location" aria-label={`Select ${l.code}`} checked={locationPick === l.id} onChange={() => setLocationPick(l.id)} className="text-indigo-600 focus:ring-indigo-500" /></td>
                        <td className="px-4 py-2.5 text-sm font-medium text-gray-900">{l.code}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{l.name}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{LOCATION_TYPE_LABELS[l.location_type] ?? l.location_type}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-600">{l.aisle ?? "—"}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-600">{l.bay ?? "—"}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-600">{l.tier ?? "—"}</td>
                        <td className="px-4 py-2.5 text-right text-sm font-mono text-gray-600">{l.capacity === null ? "—" : `${l.capacity.toLocaleString()}${l.capacity_uom_symbol ? ` ${l.capacity_uom_symbol}` : ""}`}</td>
                        <td className="px-4 py-2.5 text-sm text-gray-700">{l.is_active ? "Active" : "Inactive"}</td>
                      </tr>
                    ))}
                    {locationResults.length === 0 && (
                      <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-400">No locations found.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex justify-end gap-3 pt-5">
              <button type="button" onClick={() => setLocationSearchOpen(false)} className={CANCEL_BTN}>Cancel</button>
              <button
                type="button"
                disabled={!locationPick}
                onClick={() => { setLocationId(locationPick); setLocationSearchOpen(false); }}
                className="btn-primary"
              >
                Done
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>
    </>
  );
}
