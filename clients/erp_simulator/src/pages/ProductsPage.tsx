import { useState } from "react";
import {
  readProducts,
  deleteProduct,
  readProductBoms,
  readBomItems,
  type DBProduct,
  type DBBom,
  type DBBomItem,
} from "../api/erp";

interface BomWithItems extends DBBom {
  items: DBBomItem[];
}

export default function ProductsPage() {
  const [data, setData] = useState<DBProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [boms, setBoms] = useState<BomWithItems[]>([]);
  const [bomLoading, setBomLoading] = useState(false);

  const handleRead = async () => {
    setLoading(true);
    setError(null);
    setSelectedId(null);
    setBoms([]);
    try {
      setData(await readProducts());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Read failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    setError(null);
    try {
      await deleteProduct(id);
      setData((prev) => prev.filter((p) => p.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
        setBoms([]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  const handleSelectProduct = async (id: string) => {
    if (selectedId === id) {
      setSelectedId(null);
      setBoms([]);
      return;
    }
    setSelectedId(id);
    setBomLoading(true);
    setBoms([]);
    try {
      const bomList = await readProductBoms(id);
      const withItems: BomWithItems[] = await Promise.all(
        bomList.map(async (b) => ({
          ...b,
          items: await readBomItems(b.id),
        }))
      );
      setBoms(withItems);
    } catch {
      setBoms([]);
    } finally {
      setBomLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={handleRead}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Reading…" : "Read Products"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} products</span>
        )}
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}
      {data.length === 0 ? (
        <div className="text-center py-8 text-gray-500 bg-white rounded-lg border">
          Click &lsquo;Read Products&rsquo; to load data from the database
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Code", "Name", "Type", "Version", "UoM", "Description", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.map((row) => {
                const busy = deleting === row.id;
                const selected = selectedId === row.id;
                return (
                  <>
                    <tr
                      key={row.id}
                      onClick={() => handleSelectProduct(row.id)}
                      className={`cursor-pointer ${selected ? "bg-blue-50" : "hover:bg-gray-50"}`}
                    >
                      <td className="px-3 py-2 whitespace-nowrap">{row.code}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.name}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.product_type}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.version}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.uom}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.description ?? ""}</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(row.id); }}
                          disabled={busy}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                        >
                          {busy ? "…" : "Delete"}
                        </button>
                      </td>
                    </tr>
                    {selected && (
                      <tr key={`${row.id}-bom`}>
                        <td colSpan={7} className="px-4 py-3 bg-gray-50">
                          {bomLoading ? (
                            <span className="text-sm text-gray-500">Loading BOMs…</span>
                          ) : boms.length === 0 ? (
                            <span className="text-sm text-gray-400">No BOMs for this product</span>
                          ) : (
                            <div className="space-y-3">
                              {boms.map((bom) => (
                                <div key={bom.id} className="border rounded bg-white p-3">
                                  <div className="text-xs font-semibold text-gray-600 mb-2">
                                    BOM v{bom.version}
                                    {bom.effective_date && <span className="ml-2 font-normal">Effective: {bom.effective_date}</span>}
                                    {bom.expiry_date && <span className="ml-2 font-normal">Expires: {bom.expiry_date}</span>}
                                  </div>
                                  {bom.items.length === 0 ? (
                                    <span className="text-xs text-gray-400">No items</span>
                                  ) : (
                                    <table className="min-w-full text-xs">
                                      <thead>
                                        <tr className="text-gray-500">
                                          <th className="text-left pr-4 pb-1">Pos</th>
                                          <th className="text-left pr-4 pb-1">Material</th>
                                          <th className="text-left pr-4 pb-1">Qty</th>
                                          <th className="text-left pb-1">UoM</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {bom.items.map((item) => (
                                          <tr key={item.id}>
                                            <td className="pr-4 py-0.5">{item.position}</td>
                                            <td className="pr-4 py-0.5">{item.material_code}</td>
                                            <td className="pr-4 py-0.5">{item.quantity}</td>
                                            <td className="py-0.5">{item.uom}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
