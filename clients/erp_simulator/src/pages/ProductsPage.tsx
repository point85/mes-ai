import { useState } from "react";
import {
  readProducts,
  deleteProduct,
  cloneProduct,
  readProductBoms,
  readBomItems,
  readProductRoutes,
  readRouteSteps,
  type DBProduct,
  type DBBom,
  type DBBomItem,
  type DBRoute,
  type DBRouteStep,
} from "../api/erp";

interface BomWithItems extends DBBom {
  items: DBBomItem[];
}

interface RouteWithSteps extends DBRoute {
  steps: DBRouteStep[];
}

type DetailTab = "bom" | "routing";

export default function ProductsPage() {
  const [data, setData] = useState<DBProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("bom");
  const [boms, setBoms] = useState<BomWithItems[]>([]);
  const [routes, setRoutes] = useState<RouteWithSteps[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // Clone dialog state
  const [showClone, setShowClone] = useState(false);
  const [cloneDraft, setCloneDraft] = useState({ code: "", name: "", version: "1.0", description: "" });
  const [cloning, setCloning] = useState(false);

  const handleClone = async () => {
    if (!selectedId) return;
    setCloning(true);
    setError(null);
    try {
      const cloned = await cloneProduct(selectedId, {
        code: cloneDraft.code,
        name: cloneDraft.name,
        version: cloneDraft.version,
        description: cloneDraft.description || null,
      });
      setData((prev) => [...prev, cloned]);
      setShowClone(false);
      setCloneDraft({ code: "", name: "", version: "1.0", description: "" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Clone failed");
    } finally {
      setCloning(false);
    }
  };

  const handleRead = async () => {
    setLoading(true);
    setError(null);
    setSelectedId(null);
    setBoms([]);
    setRoutes([]);
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
        setRoutes([]);
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
      setRoutes([]);
      return;
    }
    setSelectedId(id);
    setActiveTab("bom");
    setDetailLoading(true);
    setBoms([]);
    setRoutes([]);
    try {
      const [bomList, routeList] = await Promise.all([
        readProductBoms(id),
        readProductRoutes(id),
      ]);
      const bomsWithItems = await Promise.all(
        bomList.map(async (b) => ({ ...b, items: await readBomItems(b.id) }))
      );
      const routesWithSteps = await Promise.all(
        routeList.map(async (r) => ({ ...r, steps: await readRouteSteps(r.id) }))
      );
      setBoms(bomsWithItems);
      setRoutes(routesWithSteps);
    } catch {
      setBoms([]);
      setRoutes([]);
    } finally {
      setDetailLoading(false);
    }
  };

  const renderBomPanel = () => {
    if (detailLoading) return <span className="text-sm text-gray-500">Loading…</span>;
    if (boms.length === 0) return <span className="text-sm text-gray-400">No BOMs for this product</span>;
    return (
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
    );
  };

  const renderRoutingPanel = () => {
    if (detailLoading) return <span className="text-sm text-gray-500">Loading…</span>;
    if (routes.length === 0) return <span className="text-sm text-gray-400">No routes for this product</span>;
    return (
      <div className="space-y-3">
        {routes.map((route) => (
          <div key={route.id} className="border rounded bg-white p-3">
            <div className="text-xs font-semibold text-gray-600 mb-2">
              {route.name} v{route.version}
              {route.is_default && <span className="ml-2 text-blue-600">(default)</span>}
              {route.description && <span className="ml-2 font-normal text-gray-500">{route.description}</span>}
            </div>
            {route.steps.length === 0 ? (
              <span className="text-xs text-gray-400">No steps</span>
            ) : (
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-gray-500">
                    <th className="text-left pr-4 pb-1">Seq</th>
                    <th className="text-left pr-4 pb-1">Name</th>
                    <th className="text-left pr-4 pb-1">Type</th>
                    <th className="text-left pr-4 pb-1">Cycle Time (s)</th>
                    <th className="text-left pb-1">ERP Op #</th>
                  </tr>
                </thead>
                <tbody>
                  {route.steps.map((step) => (
                    <tr key={step.id}>
                      <td className="pr-4 py-0.5">{step.sequence}</td>
                      <td className="pr-4 py-0.5">{step.name}</td>
                      <td className="pr-4 py-0.5">{step.step_type}</td>
                      <td className="pr-4 py-0.5">{step.expected_cycle_time_sec ?? "—"}</td>
                      <td className="py-0.5">{step.erp_operation_number ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* ── Clone Dialog ── */}
      {showClone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-semibold">Clone Product</h2>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col text-sm font-medium text-gray-700">
                Code *
                <input
                  className="mt-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
                  value={cloneDraft.code}
                  onChange={(e) => setCloneDraft((d) => ({ ...d, code: e.target.value }))}
                />
              </label>
              <label className="flex flex-col text-sm font-medium text-gray-700">
                Version *
                <input
                  className="mt-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
                  value={cloneDraft.version}
                  onChange={(e) => setCloneDraft((d) => ({ ...d, version: e.target.value }))}
                />
              </label>
              <label className="col-span-2 flex flex-col text-sm font-medium text-gray-700">
                Name *
                <input
                  className="mt-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
                  value={cloneDraft.name}
                  onChange={(e) => setCloneDraft((d) => ({ ...d, name: e.target.value }))}
                />
              </label>
              <label className="col-span-2 flex flex-col text-sm font-medium text-gray-700">
                Description
                <textarea
                  className="mt-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
                  rows={2}
                  value={cloneDraft.description}
                  onChange={(e) => setCloneDraft((d) => ({ ...d, description: e.target.value }))}
                />
              </label>
            </div>
            {error && (
              <div className="p-2 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setShowClone(false); setError(null); }}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleClone}
                disabled={cloning || !cloneDraft.code.trim() || !cloneDraft.name.trim() || !cloneDraft.version.trim()}
                className="px-4 py-2 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
              >
                {cloning ? "Cloning…" : "Clone"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleRead}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Reading…" : "Read Products"}
        </button>
        <button
          onClick={() => {
            const sel = data.find((p) => p.id === selectedId);
            setCloneDraft({
              code: sel ? sel.code + "-COPY" : "",
              name: sel ? sel.name + " (Copy)" : "",
              version: sel?.version ?? "1.0",
              description: sel?.description ?? "",
            });
            setShowClone(true);
          }}
          disabled={!selectedId}
          className="px-4 py-2 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50"
        >
          Clone
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
        <>
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
                    <tr
                      key={row.id}
                      onClick={() => handleSelectProduct(row.id)}
                      className={`cursor-pointer ${selected ? "bg-blue-50 border-l-2 border-blue-400" : "hover:bg-gray-50"}`}
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
                  );
                })}
              </tbody>
            </table>
          </div>

          {selectedId && (
            <div className="bg-white rounded-lg border">
              {/* Tab bar */}
              <div className="flex border-b">
                {(["bom", "routing"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 text-sm font-medium ${
                      activeTab === tab
                        ? "text-blue-600 border-b-2 border-blue-600"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {tab === "bom" ? "Bill of Materials" : "Routing"}
                  </button>
                ))}
              </div>
              {/* Tab content */}
              <div className="p-4">
                {activeTab === "bom" ? renderBomPanel() : renderRoutingPanel()}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
