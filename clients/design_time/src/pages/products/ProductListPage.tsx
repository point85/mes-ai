/**
 * Product List Page — table of product definitions with CRUD.
 * Shows code, name, version, type, and UoM.
 */

import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
  DocumentDuplicateIcon,
} from "@heroicons/react/24/outline";
import { useProducts, useDeleteProduct, useCreateProduct } from "../../hooks/useProductDef";
import type { Product } from "../../types";
import ProductFormDialog from "./ProductFormDialog";
import CloneDialog from "../../components/CloneDialog";

export default function ProductListPage() {
  const [editing, setEditing] = useState<Product | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<Product | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  const { data, isLoading, error } = useProducts();
  const deleteMut = useDeleteProduct();
  const createMut = useCreateProduct();
  const products = data?.data ?? [];

  const types = useMemo(() => {
    const set = new Set(products.map((p) => p.product_type));
    return Array.from(set).sort();
  }, [products]);

  const filtered = typeFilter
    ? products.filter((p) => p.product_type === typeFilter)
    : products;

  const handleDelete = (p: Product) => {
    if (!confirm(`Delete product "${p.code}" — ${p.name}?`)) return;
    deleteMut.mutate(p.id);
  };

  const handleClone = async (newCode: string) => {
    const p = cloneTarget!;
    await createMut.mutateAsync({
      name: p.name,
      code: newCode,
      version: p.version,
      description: p.description,
      uom_id: p.uom_id,
      product_type: p.product_type,
    });
    setCloneTarget(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Products</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define product specifications — code, version, UoM, type.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Product
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">
          Filter by type:
        </label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} product{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading products…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load products. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Version
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  UoM
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((p) => (
                <tr
                  key={p.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-indigo-600">
                    <Link to={`/products/${p.id}`} className="hover:underline">
                      {p.code}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">
                    <Link to={`/products/${p.id}`} className="hover:text-indigo-600">
                      {p.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-sm font-mono text-gray-600">
                    {p.version}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {p.product_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm font-mono text-gray-600">
                    {p.uom_symbol}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setCloneTarget(p)}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="Clone"
                      >
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditing(p)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(p)}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No products found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <ProductFormDialog
          product={editing}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}

      {/* Clone dialog */}
      {cloneTarget && (
        <CloneDialog
          title={`Clone Product — ${cloneTarget.code}`}
          label="New Code"
          initialValue={cloneTarget.code}
          onClose={() => setCloneTarget(null)}
          onConfirm={handleClone}
        />
      )}
    </div>
  );
}
