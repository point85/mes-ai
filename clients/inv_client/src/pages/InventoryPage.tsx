import { useState, useEffect, useCallback, useRef } from "react";
import { ArrowPathIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { Dialog, Transition } from "@headlessui/react";
import { Fragment } from "react";
import { MaterialLotSearchPanel } from "../components/MaterialLotSearchPanel";
import { MaterialSearchDialog } from "../components/MaterialSearchDialog";
import { LOCATION_TYPES } from "../types";
import {
  fetchInventoryTransactions,
  fetchInventoryBalances,
  fetchStorageLocations,
  fetchMaterialLots,
  fetchMaterials,
  createMaterialLot,
  updateMaterialLot,
  receiveInventory,
  putawayInventory,
  adjustInventory,
} from "../api";
import type {
  InventoryTransaction,
  InventoryBalance,
  StorageLocation,
  LocationType,
  MaterialLot,
  Material,
  MaterialLotUpdate,
  ReceivePayload,
  PutawayPayload,
  AdjustPayload,
} from "../types";

const TYPE_COLORS: Record<string, string> = {
  receive: "bg-green-100 text-green-700",
  putaway: "bg-blue-100 text-blue-700",
  pick: "bg-purple-100 text-purple-700",
  transfer: "bg-indigo-100 text-indigo-700",
  consume: "bg-red-100 text-red-700",
  adjust: "bg-gray-100 text-gray-700",
};

type PageTab = "operations" | "log";
type OpType = "receive" | "putaway" | "adjust";
type LocationField = "from_location_id" | "to_location_id" | "location_id";

const LOCATION_TYPE_LABELS: Record<LocationType, string> = { receiving: "Receiving", storage: "Storage", rip: "Raw-in-Process", staging: "Staging", shipping: "Shipping" };

const OP_LABELS: { id: OpType; label: string; color: string }[] = [
  { id: "receive", label: "Receive", color: "bg-green-600 hover:bg-green-700" },
  { id: "putaway", label: "Transfer", color: "bg-blue-600 hover:bg-blue-700" },
  { id: "adjust", label: "Adjust", color: "bg-gray-600 hover:bg-gray-700" },
];

function extractError(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const resp = (err as { response?: { data?: { message?: string; detail?: unknown } } }).response;
    if (resp?.data?.message) return resp.data.message;
    if (resp?.data?.detail) return typeof resp.data.detail === "string" ? resp.data.detail : JSON.stringify(resp.data.detail);
  }
  return err instanceof Error ? err.message : "Operation failed";
}

export function InventoryPage() {
  const [tab, setTab] = useState<PageTab>("operations");
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [locationMap, setLocationMap] = useState<Map<string, StorageLocation>>(new Map());
  const [lotMap, setLotMap] = useState<Map<string, MaterialLot>>(new Map());
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opDialog, setOpDialog] = useState<OpType | null>(null);
  const [locationSearchOpen, setLocationSearchOpen] = useState(false);
  const [locationSearchField, setLocationSearchField] = useState<LocationField | null>(null);
  const [locationSearchAllowedTypes, setLocationSearchAllowedTypes] = useState<LocationType[] | null>(null);
  const [locationCodeFilter, setLocationCodeFilter] = useState("");
  const [locationNameFilter, setLocationNameFilter] = useState("");
  const [locationTypeFilter, setLocationTypeFilter] = useState("");
  const [locationSearchResults, setLocationSearchResults] = useState<StorageLocation[] | null>(null);
  const [searchSelectedLocationId, setSearchSelectedLocationId] = useState("");
  const [materialSearchOpen, setMaterialSearchOpen] = useState(false);
  const [selectedLotId, setSelectedLotId] = useState<string | null>(null);
  const [newLotNumber, setNewLotNumber] = useState("");
  const [newLotMaterialId, setNewLotMaterialId] = useState("");
  const [lotDetails, setLotDetails] = useState({ received_date: "", expiry_date: "", supplier: "" });
  const [lotBalances, setLotBalances] = useState<InventoryBalance[]>([]);
  const [lotSearchRequest, setLotSearchRequest] = useState<{ name: string; material: string } | null>(null);
  const pendingNewLotId = useRef<string | null>(null);
  const [dialogData, setDialogData] = useState<Partial<{
    material_lot_id: string; from_location_id: string; to_location_id: string; location_id: string; quantity: number; reason: string; step_id: string;
  }>>({});

  const loadRefData = useCallback(async () => {
    try {
      const [locs, mLots, mats] = await Promise.all([fetchStorageLocations(), fetchMaterialLots(), fetchMaterials()]);
      setLocations(locs); setLots(mLots); setMaterials(mats);
      setLocationMap(new Map(locs.map((l) => [l.id, l])));
      setLotMap(new Map(mLots.map((l) => [l.id, l])));
    } catch (e) { setError("Failed to load reference data"); console.error(e); }
  }, []);

  const refreshMaterials = async () => {
    const latestMaterials = await fetchMaterials();
    setMaterials(latestMaterials);
    return latestMaterials;
  };

  useEffect(() => { loadRefData(); }, [loadRefData]);

  const loadTransactions = useCallback(async () => {
    setLoading(true); setError(null);
    try { const data = await fetchInventoryTransactions({ limit: 200 }); setTransactions(data); }
    catch (e) { setError("Failed to load transactions"); console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (tab === "log") loadTransactions(); }, [tab, loadTransactions]);

  const openLocationSearch = (field: LocationField, allowedTypes?: LocationType[]) => {
    setLocationSearchField(field);
    setLocationSearchAllowedTypes(allowedTypes ?? null);
    setLocationCodeFilter("");
    setLocationNameFilter("");
    setLocationTypeFilter("");
    setLocationSearchResults(null);
    setSearchSelectedLocationId("");
    setLocationSearchOpen(true);
  };

  const findLocations = (event: React.FormEvent) => {
    event.preventDefault();
    const codeQuery = locationCodeFilter.trim().toLowerCase();
    const nameQuery = locationNameFilter.trim().toLowerCase();
    setLocationSearchResults(locations.filter((location) =>
      (!locationSearchAllowedTypes || locationSearchAllowedTypes.includes(location.location_type)) &&
      (!locationTypeFilter || location.location_type === locationTypeFilter) &&
      location.code.toLowerCase().includes(codeQuery) &&
      location.name.toLowerCase().includes(nameQuery),
    ));
    setSearchSelectedLocationId("");
  };

  const clearLocationSearch = () => {
    setLocationCodeFilter("");
    setLocationNameFilter("");
    setLocationTypeFilter("");
    setLocationSearchResults(null);
    setSearchSelectedLocationId("");
    if (locationSearchField) setDialogData((d) => ({ ...d, [locationSearchField]: "" }));
  };

  const selectSearchedLocation = () => {
    if (!locationSearchField || !searchSelectedLocationId) return;
    setDialogData({ ...dialogData, [locationSearchField]: searchSelectedLocationId });
    setLocationSearchOpen(false);
  };

  const onHandAt = (locationId: string) => lotBalances.find((b) => b.location_id === locationId)?.quantity_on_hand;

  const changePutawayFrom = (locationId: string) => {
    setDialogData((d) => ({ ...d, from_location_id: locationId, quantity: onHandAt(locationId) }));
  };

  const renderLocationPicker = (field: LocationField, label: string, allowedTypes?: LocationType[]) => {
    const selected = locations.find((location) => location.id === dialogData[field]);
    return (
      <div>
        <label htmlFor={`location-${field}`} className="mb-1 block text-sm font-medium text-gray-700">{label} *</label>
        <div className="flex gap-2">
          <input id={`location-${field}`} type="text" value={selected ? `${selected.code} - ${selected.name}` : ""} placeholder="Select a location" readOnly required className="input-field min-w-0 flex-1" />
          <button type="button" onClick={() => openLocationSearch(field, allowedTypes)} aria-label={`Search ${label.toLowerCase()}`} title={`Search ${label.toLowerCase()}`} className="inline-flex shrink-0 items-center justify-center rounded-md border border-gray-300 bg-white px-3 text-gray-700 hover:bg-gray-50">
            <MagnifyingGlassIcon className="h-5 w-5" />
          </button>
        </div>
      </div>
    );
  };

  const resetOpForm = () => {
    setDialogData({});
    pendingNewLotId.current = null;
    setNewLotNumber("");
    setNewLotMaterialId("");
    setLotDetails({ received_date: "", expiry_date: "", supplier: "" });
    setLotBalances([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError(null);
    try {
      // Drop empty optional fields so the backend doesn't try to validate blank strings as UUID/enum
      const payload = Object.fromEntries(
        Object.entries(dialogData).filter(([, v]) => v !== "" && v !== undefined)
      );
      switch (opDialog) {
        case "receive": {
          const receivedDate = lotDetails.received_date || null;
          const expiryDate = lotDetails.expiry_date || null;
          const supplier = lotDetails.supplier.trim() || null;
          let lotId = selectedLotId;
          if (!lotId) {
            // A lot created by an earlier attempt whose receive step failed is reused instead of duplicated.
            if (!pendingNewLotId.current) {
              const created = await createMaterialLot({ material_id: newLotMaterialId, lot_number: newLotNumber.trim(), tracking_method: "lot", quantity_on_hand: dialogData.quantity ?? 0, received_date: receivedDate, expiry_date: expiryDate, supplier });
              pendingNewLotId.current = created.id;
            }
            lotId = pendingNewLotId.current;
          } else {
            const current = lotMap.get(lotId);
            const changes: MaterialLotUpdate = {};
            if (receivedDate && receivedDate !== current?.received_date) changes.received_date = receivedDate;
            if (expiryDate && expiryDate !== current?.expiry_date) changes.expiry_date = expiryDate;
            if (supplier && supplier !== current?.supplier) changes.supplier = supplier;
            if (Object.keys(changes).length > 0) { await updateMaterialLot(lotId, changes); }
          }
          await receiveInventory({ ...payload, material_lot_id: lotId } as unknown as ReceivePayload);
          if (!selectedLotId) {
            pendingNewLotId.current = null;
            setLotSearchRequest({ name: newLotNumber.trim(), material: materials.find((m) => m.id === newLotMaterialId)?.name ?? "" });
          }
          await loadRefData();
          break;
        }
        case "putaway": await putawayInventory({ ...payload, material_lot_id: selectedLotId } as unknown as PutawayPayload); break;
        case "adjust": await adjustInventory({ ...payload, material_lot_id: selectedLotId } as unknown as AdjustPayload); await loadRefData(); break;
      }
      setOpDialog(null); resetOpForm();
      if (tab === "log") loadTransactions();
    } catch (e) { setError(extractError(e)); }
    finally { setLoading(false); }
  };

  const openDialog = (type: OpType) => {
    setOpDialog(type);
    pendingNewLotId.current = null;
    setNewLotNumber("");
    setNewLotMaterialId("");
    const selectedLot = selectedLotId ? lotMap.get(selectedLotId) : undefined;
    setLotDetails(type === "receive" && selectedLot ? { received_date: selectedLot.received_date ?? "", expiry_date: selectedLot.expiry_date ?? "", supplier: selectedLot.supplier ?? "" } : { received_date: "", expiry_date: "", supplier: "" });
    const defaults: Partial<typeof dialogData> = {};
    if (type === "receive") {
      if (selectedLotId) defaults.to_location_id = locations.find((l) => l.location_type === "receiving")?.id ?? "";
    }
    else if (type === "putaway") {
      setLotBalances([]);
      if (selectedLotId) {
        fetchInventoryBalances({ material_lot_id: selectedLotId })
          .then((bals) => {
            const held = bals.filter((b) => b.quantity_on_hand > 0);
            setLotBalances(held);
            if (held.length === 1) setDialogData((d) => ({ ...d, from_location_id: held[0].location_id, quantity: held[0].quantity_on_hand }));
          })
          .catch((e) => setError(extractError(e)));
      }
    }
    else if (type === "adjust") {
      setLotBalances([]);
      if (selectedLotId) {
        fetchInventoryBalances({ material_lot_id: selectedLotId })
          .then((bals) => {
            const held = bals.filter((b) => b.quantity_on_hand > 0);
            setLotBalances(held);
            if (held.length === 1) setDialogData((d) => ({ ...d, location_id: held[0].location_id, quantity: held[0].quantity_on_hand }));
          })
          .catch((e) => setError(extractError(e)));
      }
    }
    setDialogData(defaults);
  };

  const dialogTitle = opDialog ? OP_LABELS.find((o) => o.id === opDialog)?.label : "";
  const newLotMaterialName = materials.find((m) => m.id === newLotMaterialId)?.name ?? "";
  const operationMaterialId = selectedLotId ? lotMap.get(selectedLotId)?.material_id : newLotMaterialId;
  const operationMaterial = materials.find((material) => material.id === operationMaterialId);
  const operationMaterialUom = operationMaterial?.uom_symbol;

  const changeReceivedDate = (receivedDate: string) => {
    const shelfLifeDays = operationMaterial?.shelf_life_days;
    let expiryDate = lotDetails.expiry_date;
    if (receivedDate && shelfLifeDays) {
      const expiry = new Date(`${receivedDate}T00:00:00Z`);
      expiry.setUTCDate(expiry.getUTCDate() + shelfLifeDays);
      expiryDate = expiry.toISOString().slice(0, 10);
    }
    setLotDetails({ ...lotDetails, received_date: receivedDate, expiry_date: expiryDate });
  };
  const canExecute = opDialog === "receive"
    ? !!dialogData.to_location_id && (!!selectedLotId || (!!newLotMaterialId && !!newLotNumber.trim()))
    : opDialog === "putaway"
      ? !!selectedLotId && !!dialogData.from_location_id && !!dialogData.to_location_id
      : opDialog === "adjust"
        ? !!selectedLotId && !!dialogData.location_id
        : true;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-2xl font-bold text-gray-900">MES AI - Inventory</h1></div>
      </div>
      {error && <div className="flex items-center gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700"><span className="flex-shrink-0">⚠</span>{error}</div>}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {[{ id: "operations", label: "Operations" }, { id: "log", label: "Transaction Log" }].map((t) => (
            <button key={t.id} onClick={() => setTab(t.id as PageTab)} className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${tab === t.id ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}`}>{t.label}</button>
          ))}
        </nav>
      </div>
      {tab === "operations" && <MaterialLotSearchPanel lots={lots} materials={materials} selectedLotId={selectedLotId} onSelectLot={setSelectedLotId} searchRequest={lotSearchRequest} />}
      {tab === "log" && <LogTab transactions={transactions} loading={loading} locationMap={locationMap} lotMap={lotMap} loadTransactions={loadTransactions} />}

      {/* Action bar — Operations tab only */}
      {tab === "operations" && <div className="bg-white rounded-lg shadow-md p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {OP_LABELS.map((op) => (
            <button key={op.id} onClick={() => openDialog(op.id)} disabled={(op.id === "putaway" || op.id === "adjust") && !selectedLotId} title={(op.id === "putaway" || op.id === "adjust") && !selectedLotId ? "Find and select a material lot first" : undefined} className={`flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-medium text-white shadow-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${op.color}`}>
              {op.label}
            </button>
          ))}
        </div>
      </div>}

      <Transition appear show={opDialog !== null} as={Dialog} onClose={() => { setOpDialog(null); resetOpForm(); }}>
        <Dialog.Panel className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0 scale-95" enterTo="opacity-100 scale-100" leave="ease-in duration-200" leaveFrom="opacity-100 scale-100" leaveTo="opacity-0 scale-95">
            <Dialog.Panel className="w-full max-w-md bg-white rounded-lg shadow-xl p-6">
              <Dialog.Title className="text-lg font-semibold text-gray-900 mb-4">{dialogTitle}</Dialog.Title>
              <form onSubmit={handleSubmit} className="space-y-4">
                {opDialog === "receive" && !selectedLotId && <>
                    <div>
                      <label htmlFor="new-lot-number" className="mb-1 block text-sm font-medium text-gray-700">Lot Number *</label>
                      <input id="new-lot-number" type="text" value={newLotNumber} onChange={(e) => { setNewLotNumber(e.target.value); pendingNewLotId.current = null; }} required className="input-field" />
                    </div>
                    <div>
                      <label htmlFor="new-lot-material" className="mb-1 block text-sm font-medium text-gray-700">Material *</label>
                      <div className="flex gap-2">
                        <input id="new-lot-material" type="text" value={newLotMaterialName} placeholder="Select a material" readOnly className="input-field min-w-0 flex-1" />
                        <button type="button" onClick={() => setMaterialSearchOpen(true)} aria-label="Search materials" title="Search materials" className="inline-flex shrink-0 items-center justify-center rounded-md border border-gray-300 bg-white px-3 text-gray-700 hover:bg-gray-50">
                          <MagnifyingGlassIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  </>}
                {opDialog === "receive" && renderLocationPicker("to_location_id", "To Location", ["receiving"])}
                {opDialog === "adjust" && lotBalances.length > 1 && (
                  <div>
                    <label htmlFor="adjust-location" className="mb-1 block text-sm font-medium text-gray-700">Location *</label>
                    <select id="adjust-location" value={dialogData.location_id ?? ""} onChange={(e) => setDialogData({ ...dialogData, location_id: e.target.value, quantity: onHandAt(e.target.value) })} required className="input-field">
                      <option value="">Select location</option>
                      {lotBalances.map((b) => { const loc = locationMap.get(b.location_id); return <option key={b.id} value={b.location_id}>{loc ? `${loc.code} - ${loc.name}` : b.location_id.slice(0, 8)}</option>; })}
                    </select>
                  </div>
                )}
                {opDialog === "putaway" && <>
                  <div>
                    <label htmlFor="putaway-from" className="mb-1 block text-sm font-medium text-gray-700">From Location *</label>
                    <select id="putaway-from" value={dialogData.from_location_id ?? ""} onChange={(e) => changePutawayFrom(e.target.value)} required className="input-field">
                      <option value="">Select location</option>
                      {lotBalances.map((b) => { const loc = locationMap.get(b.location_id); return <option key={b.id} value={b.location_id}>{loc ? `${loc.code} - ${loc.name}` : b.location_id.slice(0, 8)}</option>; })}
                    </select>
                  </div>
                  {renderLocationPicker("to_location_id", "To Location", ["storage", "rip", "staging"])}
                </>}
                <div className="flex items-end gap-3">
                  <div className="min-w-0 flex-1"><label htmlFor="operation-quantity" className="block text-sm font-medium text-gray-700 mb-1">Quantity *</label><input id="operation-quantity" type="number" name="quantity" value={dialogData.quantity ?? ""} onChange={(e) => setDialogData({ ...dialogData, quantity: Number(e.target.value) })} required min={opDialog === "adjust" ? "0" : "0.01"} step="any" className="input-field" /></div>
                  {opDialog !== null && <div className="w-28 shrink-0"><span className="mb-1 block text-sm font-medium text-gray-700">UoM</span><div aria-label="Unit of measure" className="input-field flex items-center bg-gray-50 text-gray-500">{operationMaterialUom ?? "—"}</div></div>}
                </div>
                {opDialog === "receive" && <>
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Received Date</label><input type="date" name="received_date" value={lotDetails.received_date} onChange={(e) => changeReceivedDate(e.target.value)} className="input-field" /></div>
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Expiry Date</label><input type="date" name="expiry_date" value={lotDetails.expiry_date} onChange={(e) => setLotDetails({ ...lotDetails, expiry_date: e.target.value })} className="input-field" /></div>
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Supplier</label><input type="text" name="supplier" value={lotDetails.supplier} onChange={(e) => setLotDetails({ ...lotDetails, supplier: e.target.value })} className="input-field" /></div>
                </>}
                <div><label className="block text-sm font-medium text-gray-700 mb-1">{opDialog === "receive" || opDialog === "putaway" ? "Reference" : "Reason"}</label><textarea name="reason" value={dialogData.reason ?? ""} onChange={(e) => setDialogData({ ...dialogData, reason: e.target.value })} rows={2} className="input-field" /></div>
                <div className="flex justify-end gap-3 pt-4"><button type="button" onClick={() => { setOpDialog(null); resetOpForm(); }} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button><button type="submit" disabled={loading || !canExecute} className="btn-primary">{loading ? "Processing..." : "Execute"}</button></div>
              </form>
            </Dialog.Panel>
          </Transition.Child>
        </Dialog.Panel>
      </Transition>
      <MaterialSearchDialog open={materialSearchOpen} refreshMaterials={refreshMaterials} onClose={() => setMaterialSearchOpen(false)} onSelect={(id) => { setNewLotMaterialId(id); pendingNewLotId.current = null; }} onClear={() => { setNewLotMaterialId(""); pendingNewLotId.current = null; }} />
      <Transition appear show={locationSearchOpen} as={Dialog} onClose={() => setLocationSearchOpen(false)}>
        <Dialog.Panel className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4">
          <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0 scale-95" enterTo="opacity-100 scale-100" leave="ease-in duration-200" leaveFrom="opacity-100 scale-100" leaveTo="opacity-0 scale-95">
            <Dialog.Panel className="w-full max-w-5xl rounded-lg bg-white p-6 shadow-xl">
              <Dialog.Title className="mb-4 text-lg font-semibold text-gray-900">Find Storage Location</Dialog.Title>
              <form onSubmit={findLocations} className="flex flex-col items-end gap-3 sm:flex-row">
                <div className="w-full flex-1">
                  <label htmlFor="location-code-filter" className="mb-1 block text-sm font-medium text-gray-700">Code</label>
                  <input id="location-code-filter" type="text" value={locationCodeFilter} onChange={(event) => setLocationCodeFilter(event.target.value)} className="input-field" />
                </div>
                <div className="w-full flex-1">
                  <label htmlFor="location-name-filter" className="mb-1 block text-sm font-medium text-gray-700">Name</label>
                  <input id="location-name-filter" type="text" value={locationNameFilter} onChange={(event) => setLocationNameFilter(event.target.value)} className="input-field" />
                </div>
                {opDialog !== "receive" && opDialog !== "putaway" && <div className="w-full sm:w-56">
                  <label htmlFor="location-type-filter" className="mb-1 block text-sm font-medium text-gray-700">Type</label>
                  <select id="location-type-filter" value={locationTypeFilter} onChange={(event) => setLocationTypeFilter(event.target.value)} className="input-field">
                    <option value="">All types</option>
                    {LOCATION_TYPES.filter((type) => !locationSearchAllowedTypes || locationSearchAllowedTypes.includes(type)).map((type) => <option key={type} value={type}>{LOCATION_TYPE_LABELS[type]}</option>)}
                  </select>
                </div>}
                <div className="flex shrink-0 gap-2">
                  <button type="button" onClick={clearLocationSearch} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Clear</button>
                  <button type="submit" className="btn-primary">Find</button>
                </div>
              </form>

              {locationSearchResults !== null && (
                <div className="mt-5 max-h-[55vh] overflow-auto rounded-md border border-gray-200">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Select</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Code</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Type</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Aisle</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Bay</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Tier</th>
                        <th scope="col" className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Capacity</th>
                        <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {locationSearchResults.map((location) => (
                        <tr key={location.id} onClick={() => setSearchSelectedLocationId(location.id)} className={`cursor-pointer ${searchSelectedLocationId === location.id ? "bg-indigo-50" : "hover:bg-gray-50"}`}>
                          <td className="px-4 py-2.5"><input type="radio" name="selected-location" aria-label={`Select ${location.code}`} checked={searchSelectedLocationId === location.id} onChange={() => setSearchSelectedLocationId(location.id)} className="text-indigo-600 focus:ring-indigo-500" /></td>
                          <td className="px-4 py-2.5 text-sm font-medium text-gray-900">{location.code}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-700">{location.name}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-700">{LOCATION_TYPE_LABELS[location.location_type] ?? location.location_type}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-600">{location.aisle ?? "—"}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-600">{location.bay ?? "—"}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-600">{location.tier ?? "—"}</td>
                          <td className="px-4 py-2.5 text-right text-sm font-mono text-gray-600">{location.capacity === null ? "—" : `${location.capacity.toLocaleString()}${location.capacity_uom_symbol ? ` ${location.capacity_uom_symbol}` : ""}`}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-700">{location.is_active ? "Active" : "Inactive"}</td>
                        </tr>
                      ))}
                      {locationSearchResults.length === 0 && (
                        <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-400">No locations found.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-5">
                <button type="button" onClick={() => setLocationSearchOpen(false)} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="button" onClick={selectSearchedLocation} disabled={!searchSelectedLocationId} className="btn-primary disabled:cursor-not-allowed disabled:opacity-50">Done</button>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </Dialog.Panel>
      </Transition>
    </div>
  );
}

type DateRange = "today" | "yesterday" | "this_week" | "last_week" | "this_month" | "last_month";

const DATE_RANGE_OPTIONS: { id: DateRange; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "yesterday", label: "Yesterday" },
  { id: "this_week", label: "This Week" },
  { id: "last_week", label: "Last Week" },
  { id: "this_month", label: "This Month" },
  { id: "last_month", label: "Last Month" },
];

// Returns [start, end) in local time; weeks start on Monday.
function dateRangeBounds(range: DateRange): [Date, Date] {
  const now = new Date();
  const day = (offset: number) => new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);
  const weekStart = day(-((now.getDay() + 6) % 7));
  switch (range) {
    case "today": return [day(0), day(1)];
    case "yesterday": return [day(-1), day(0)];
    case "this_week": return [weekStart, new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + 7)];
    case "last_week": return [new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() - 7), weekStart];
    case "this_month": return [new Date(now.getFullYear(), now.getMonth(), 1), new Date(now.getFullYear(), now.getMonth() + 1, 1)];
    case "last_month": return [new Date(now.getFullYear(), now.getMonth() - 1, 1), new Date(now.getFullYear(), now.getMonth(), 1)];
  }
}

function LogTab({ transactions: allTransactions, loading, locationMap, lotMap, loadTransactions }: any) {
  const [dateRange, setDateRange] = useState<DateRange>("today");
  const [rangeStart, rangeEnd] = dateRangeBounds(dateRange);
  const transactions = allTransactions.filter((txn: InventoryTransaction) => {
    const performed = new Date(txn.performed_at);
    return performed >= rangeStart && performed < rangeEnd;
  });
  const locName = (id: string | null) => { if (!id) return "—"; const loc = locationMap.get(id); return loc ? `${loc.code} (${loc.location_type})` : id.slice(0, 8); };
  const lotLabel = (id: string) => { const lot = lotMap.get(id); if (!lot) return id.slice(0, 8); return lot.tracking_method === "serial" ? `${lot.lot_number} [SN: ${lot.serial_number}]` : lot.lot_number; };
  const trackingBadge = (method: any) => { if (!method) return <span className="text-gray-400">—</span>; return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${method === "serial" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"}`}>{method === "serial" ? "Serial" : "Lot"}</span>; };
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 bg-white p-4 rounded-lg shadow-md"><div className="flex items-center gap-2"><label htmlFor="log-date-range" className="text-sm font-medium text-gray-700">Date</label><select id="log-date-range" value={dateRange} onChange={(e) => setDateRange(e.target.value as DateRange)} className="input-field">{DATE_RANGE_OPTIONS.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></div><button onClick={loadTransactions} disabled={loading} className="ml-auto flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"><ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh</button></div>
      <div className="rounded-lg bg-white shadow-md overflow-hidden">
        {loading ? <div className="p-8 text-center text-gray-500"><ArrowPathIcon className="mx-auto h-8 w-8 animate-spin text-indigo-600" /><p className="mt-2">Loading transactions...</p></div> : transactions.length === 0 ? <div className="p-8 text-center text-gray-500"><MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-300" /><p className="mt-2 text-lg">No transactions found</p><p className="mt-1 text-sm">Perform operations to see transactions</p></div> : <div className="overflow-x-auto"><table className="min-w-full divide-y divide-gray-200"><thead className="bg-gray-50"><tr><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Material Lot</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tracking</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">From Location</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">To Location</th><th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Qty</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reference</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reason</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Performed At</th></tr></thead><tbody className="bg-white divide-y divide-gray-200">{transactions.map((txn: InventoryTransaction) => <tr key={txn.id} className="hover:bg-gray-50"><td className="px-4 py-3 text-sm"><span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${TYPE_COLORS[txn.transaction_type] || "bg-gray-100 text-gray-700"}`}>{txn.transaction_type}</span></td><td className="px-4 py-3 text-sm text-gray-900">{lotLabel(txn.material_lot_id)}</td><td className="px-4 py-3 text-sm">{trackingBadge(txn.material_lot_tracking_method)}</td><td className="px-4 py-3 text-sm text-gray-600">{locName(txn.from_location_id)}</td><td className="px-4 py-3 text-sm text-gray-600">{locName(txn.to_location_id)}</td><td className="px-4 py-3 text-sm text-right font-mono text-gray-900">{txn.quantity.toLocaleString()}</td><td className="px-4 py-3 text-sm text-gray-500">{txn.reference_type && txn.reference_id ? <> {txn.reference_type}: {txn.reference_id.slice(0, 8)} </> : <span className="text-gray-400">—</span>}</td><td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">{txn.reason ?? "—"}</td><td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{new Date(txn.performed_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
      </div>
    </div>
  );
}
