/**
 * BOM Editor Page — manages BOMs (headers) and their line items for a product.
 * URL: /products/:productId/boms
 *
 * Two-panel layout:
 *   Left:  BOM list (create / edit / delete)
 *   Right: BOM items for the selected BOM (create / edit / delete)
 */

import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  ArrowLeftIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import {
  useBOMs,
  useBOMItems,
  useDeleteBOM,
  useDeleteBOMItem,
  useRoutes,
  useRouteSteps,
} from "../../hooks/useProductDef";
import { fetchProduct } from "../../api/productDef";
import type { BOM, BOMItem } from "../../types";
import BOMFormDialog from "./BOMFormDialog";
import BOMItemFormDialog from "./BOMItemFormDialog";

export default function BOMEditorPage() {
  const { productId } = useParams<{ productId: string }>();
  const [selectedBom, setSelectedBom] = useState<BOM | null>(null);
  const [showBomForm, setShowBomForm] = useState(false);
  const [editingBom, setEditingBom] = useState<BOM | null>(null);
  const [showItemForm, setShowItemForm] = useState(false);
  const [editingItem, setEditingItem] = useState<BOMItem | null>(null);

  // Product header
  const { data: product } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => fetchProduct(productId!),
    enabled: !!productId,
  });

  // BOMs for this product
  const { data: bomsData, isLoading: bomsLoading } = useBOMs(productId ?? "");
  const boms = bomsData?.data ?? [];

  // Auto-select the first BOM when loaded
  useEffect(() => {
    if (!selectedBom && boms.length > 0) {
      setSelectedBom(boms[0]);
    }
    // If the selected BOM disappears (delete), fall back to first
    if (selectedBom && !boms.find((b) => b.id === selectedBom.id)) {
      setSelectedBom(boms[0] ?? null);
    }
  }, [boms, selectedBom]);

  // Routes → steps for the step-picker dropdown in the item dialog
  const { data: routesData } = useRoutes(productId ?? "");
  const routes = routesData?.data ?? [];
  const defaultRouteId =
    routes.find((r) => r.is_default)?.id ?? routes[0]?.id ?? "";
  const { data: stepsData } = useRouteSteps(defaultRouteId);
  const steps = (stepsData?.data ?? []).slice().sort((a, b) => a.sequence - b.sequence);
  const stepNameMap = new Map(
    steps.map((s) => [s.id, `${s.sequence}. ${s.name}`]),
  );

  // Items for the selected BOM
  const { data: itemsData, isLoading: itemsLoading } = useBOMItems(
    selectedBom?.id ?? "",
  );
  const items = (itemsData?.data ?? [])
    .slice()
    .sort((a, b) => a.position - b.position);

  const deleteBomMut = useDeleteBOM();
  const deleteItemMut = useDeleteBOMItem();

  const handleDeleteBom = (b: BOM) => {
    if (
      confirm(
        `Delete BOM v${b.version}? All items on this BOM will be soft-deleted.`,
      )
    ) {
      deleteBomMut.mutate(b.id, {
        onSuccess: () => {
          if (selectedBom?.id === b.id) setSelectedBom(null);
        },
      });
    }
  };

  const handleDeleteItem = (it: BOMItem) => {
    if (confirm(`Delete BOM item ${it.material_code}?`)) {
      deleteItemMut.mutate(it.id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link
          to="/products"
          className="flex items-center gap-1 hover:text-indigo-600 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Products
        </Link>
        <ChevronRightIcon className="h-3 w-3" />
        {product && (
          <>
            <Link
              to={`/products/${productId}`}
              className="hover:text-indigo-600 transition-colors"
            >
              {product.code}
            </Link>
            <ChevronRightIcon className="h-3 w-3" />
          </>
        )}
        <span className="font-medium text-gray-900">BOMs</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            Bills of Material
          </h1>
          {product && (
            <p className="mt-0.5 text-sm text-gray-500">
              {product.name} · {product.code} v{product.version}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ─── Left panel: BOM list ─────────────────────────────── */}
        <div className="lg:col-span-1">
          <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">BOMs</h2>
              <button
                onClick={() => {
                  setEditingBom(null);
                  setShowBomForm(true);
                }}
                className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
              >
                <PlusIcon className="h-3.5 w-3.5" />
                New BOM
              </button>
            </div>

            {bomsLoading ? (
              <p className="px-4 py-4 text-sm text-gray-500">Loading…</p>
            ) : boms.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-gray-400">No BOMs defined.</p>
                <p className="mt-1 text-xs text-gray-400">
                  Create one to list the materials consumed by this product.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {boms.map((b) => {
                  const isSel = selectedBom?.id === b.id;
                  return (
                    <div
                      key={b.id}
                      onClick={() => setSelectedBom(b)}
                      className={`cursor-pointer px-4 py-3 transition-colors ${
                        isSel ? "bg-indigo-50" : "hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            Version {b.version}
                          </div>
                          <div className="text-xs text-gray-500">
                            {b.effective_date ? (
                              <>Effective {b.effective_date}</>
                            ) : (
                              <>No effective date</>
                            )}
                            {b.expiry_date && <> · Expires {b.expiry_date}</>}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingBom(b);
                              setShowBomForm(true);
                            }}
                            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                            title="Edit"
                          >
                            <PencilSquareIcon className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteBom(b);
                            }}
                            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                            title="Delete"
                          >
                            <TrashIcon className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ─── Right panel: BOM items ───────────────────────────── */}
        <div className="lg:col-span-2">
          {!selectedBom ? (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
              <p className="text-sm text-gray-500">
                Select or create a BOM to manage its items.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">
                    Items for BOM v{selectedBom.version}
                  </h2>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {items.length}{" "}
                    {items.length === 1 ? "item" : "items"}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setEditingItem(null);
                    setShowItemForm(true);
                  }}
                  className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
                >
                  <PlusIcon className="h-3.5 w-3.5" />
                  Add Item
                </button>
              </div>

              {itemsLoading ? (
                <p className="px-4 py-4 text-sm text-gray-500">Loading…</p>
              ) : items.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <p className="text-sm text-gray-400">
                    No line items on this BOM.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Pos
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Material
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          Qty
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          UoM
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Consumed At Step
                        </th>
                        <th className="px-4 py-2" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {items.map((it) => (
                        <tr
                          key={it.id}
                          className="hover:bg-gray-50 transition-colors"
                        >
                          <td className="px-4 py-2 text-sm text-gray-600">
                            {it.position}
                          </td>
                          <td className="px-4 py-2 text-sm font-medium text-gray-900">
                            {it.material_code}
                          </td>
                          <td className="px-4 py-2 text-right text-sm text-gray-700">
                            {it.quantity}
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-600">
                            {it.uom}
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-600">
                            {it.process_segment_id
                              ? stepNameMap.get(it.process_segment_id) ??
                                it.process_segment_id.slice(0, 8)
                              : (
                                <span className="text-gray-400">—</span>
                              )}
                          </td>
                          <td className="px-4 py-2 text-right">
                            <div className="inline-flex items-center gap-1">
                              <button
                                onClick={() => {
                                  setEditingItem(it);
                                  setShowItemForm(true);
                                }}
                                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                                title="Edit"
                              >
                                <PencilSquareIcon className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteItem(it)}
                                className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                                title="Delete"
                              >
                                <TrashIcon className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Dialogs */}
      {showBomForm && productId && (
        <BOMFormDialog
          productId={productId}
          bom={editingBom}
          onClose={() => {
            setShowBomForm(false);
            setEditingBom(null);
          }}
        />
      )}
      {showItemForm && selectedBom && (
        <BOMItemFormDialog
          bomId={selectedBom.id}
          item={editingItem}
          steps={steps}
          onClose={() => {
            setShowItemForm(false);
            setEditingItem(null);
          }}
        />
      )}
    </div>
  );
}
