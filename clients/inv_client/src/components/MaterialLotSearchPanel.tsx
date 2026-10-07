import { useEffect, useState } from "react";
import { MagnifyingGlassIcon, MapPinIcon } from "@heroicons/react/24/outline";
import { LotLocationsDialog } from "./LotLocationsDialog";
import type { MaterialLot, Material } from "../types";

interface Props {
  lots: MaterialLot[];
  materials: Material[];
  selectedLotId: string | null;
  onSelectLot: (lotId: string | null) => void;
  searchRequest: { name: string; material: string } | null;
}

export function MaterialLotSearchPanel({ lots, materials, selectedLotId, onSelectLot, searchRequest }: Props) {
  const [nameInput, setNameInput] = useState("");
  const [materialInput, setMaterialInput] = useState("");
  const [filters, setFilters] = useState({ name: "", material: "" });
  const [searched, setSearched] = useState(false);
  const [locationLot, setLocationLot] = useState<MaterialLot | null>(null);
  const [locationDialogOpen, setLocationDialogOpen] = useState(false);

  const materialText = (lot: MaterialLot) => materials.find((m) => m.id === lot.material_id)?.name ?? lot.material_name ?? "";
  const materialLabel = (lot: MaterialLot) => {
    const m = materials.find((x) => x.id === lot.material_id);
    return m ? `${m.code} - ${m.name}` : lot.material_id;
  };
  const materialUom = (lot: MaterialLot) => materials.find((m) => m.id === lot.material_id)?.uom_symbol;

  const results = !searched ? [] : lots.filter((lot) =>
    lot.lot_number.toLowerCase().includes(filters.name) &&
    materialText(lot).toLowerCase().includes(filters.material),
  );

  const runSearch = (name: string, material: string) => {
    setFilters({ name: name.trim().toLowerCase(), material: material.trim().toLowerCase() });
    setSearched(true);
    onSelectLot(null);
  };

  const find = (event: React.FormEvent) => {
    event.preventDefault();
    runSearch(nameInput, materialInput);
  };

  useEffect(() => {
    if (!searchRequest) return;
    setNameInput(searchRequest.name);
    setMaterialInput(searchRequest.material);
    runSearch(searchRequest.name, searchRequest.material);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchRequest]);

  const clear = () => {
    setNameInput("");
    setMaterialInput("");
    setFilters({ name: "", material: "" });
    setSearched(false);
    onSelectLot(null);
  };

  const headerClass = "px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider";

  return (
    <div className="space-y-4">
      <form onSubmit={find} className="flex flex-col items-end gap-3 rounded-lg bg-white p-4 shadow-md sm:flex-row">
        <div className="w-full flex-1">
          <label htmlFor="ops-lot-name-filter" className="mb-1 block text-sm font-medium text-gray-700">Lot Number</label>
          <input id="ops-lot-name-filter" type="text" value={nameInput} onChange={(e) => setNameInput(e.target.value)} className="input-field" />
        </div>
        <div className="w-full flex-1">
          <label htmlFor="ops-lot-material-filter" className="mb-1 block text-sm font-medium text-gray-700">Material Name</label>
          <input id="ops-lot-material-filter" type="text" value={materialInput} onChange={(e) => setMaterialInput(e.target.value)} className="input-field" />
        </div>
        <div className="flex shrink-0 gap-2">
          <button type="button" onClick={clear} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Clear</button>
          <button type="submit" className="btn-primary">Find</button>
        </div>
      </form>
      <div className="rounded-lg bg-white shadow-md overflow-hidden">
        {results.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-2 text-lg">No material lots found</p>
            <p className="mt-1 text-sm">{!searched ? "Enter search criteria and click Find to display material lots" : "No lots match the current filters"}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className={`${headerClass} text-left`}>Select</th>
                  <th className={`${headerClass} text-left`}>Lot Number</th>
                  <th className={`${headerClass} text-left`}>Material</th>
                  <th className={`${headerClass} text-left`}>Location</th>
                  <th className={`${headerClass} text-right`}>On Hand</th>
                  <th className={`${headerClass} text-left`}>Status</th>
                  <th className={`${headerClass} text-left`}>Received</th>
                  <th className={`${headerClass} text-left`}>Expiry</th>
                  <th className={`${headerClass} text-left`}>Supplier</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {results.map((lot) => (
                  <tr key={lot.id} onClick={() => onSelectLot(selectedLotId === lot.id ? null : lot.id)} className={`cursor-pointer ${selectedLotId === lot.id ? "bg-indigo-50" : "hover:bg-gray-50"}`}>
                    <td className="px-4 py-3"><input type="radio" name="selected-lot" aria-label={`Select lot ${lot.lot_number}`} checked={selectedLotId === lot.id} onChange={() => undefined} className="text-indigo-600 focus:ring-indigo-500" /></td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{lot.lot_number}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{materialLabel(lot)}</td>
                    <td className="px-4 py-3 text-sm">
                      <button type="button" onClick={(e) => { e.stopPropagation(); setLocationLot(lot); setLocationDialogOpen(true); }} title="View storage locations" aria-label={`View storage locations for ${lot.lot_number}`} className="text-indigo-600 hover:text-indigo-900"><MapPinIcon className="h-4 w-4" /></button>
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-mono text-gray-900">{lot.quantity_on_hand.toLocaleString()}{materialUom(lot) ? ` ${materialUom(lot)}` : ""}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{lot.status}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{lot.received_date ? new Date(lot.received_date).toLocaleDateString() : "—"}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{lot.expiry_date ? new Date(lot.expiry_date).toLocaleDateString() : "—"}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{lot.supplier ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <LotLocationsDialog lot={locationLot} uomSymbol={locationLot ? materialUom(locationLot) ?? null : null} open={locationDialogOpen} onClose={() => setLocationDialogOpen(false)} />
    </div>
  );
}
