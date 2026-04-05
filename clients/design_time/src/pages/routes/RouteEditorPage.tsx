/**
 * Route Editor Page — standalone manufacturing route editor.
 * URL: /routes
 *
 * Three-panel layout:
 *   Left:   route list + create button
 *   Center: steps table for the selected route
 *   Right:  product assignments for the selected route
 */

import { useState } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  ChevronRightIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  useAllRoutes,
  useRouteSteps,
  useRouteProducts,
  useProducts,
  useAssignProductToRoute,
  useUnassignProductFromRoute,
} from "../../hooks/useProductDef";
import type { ProcessRoute, RouteStep, Product } from "../../types";
import RouteCreateDialog from "./RouteCreateDialog";
import StepFormDialog from "../products/StepFormDialog";

export default function RouteEditorPage() {
  const [selectedRoute, setSelectedRoute] = useState<ProcessRoute | null>(null);
  const [showRouteForm, setShowRouteForm] = useState(false);
  const [showStepForm, setShowStepForm] = useState(false);
  const [editingStep, setEditingStep] = useState<RouteStep | null>(null);
  const [showProductPicker, setShowProductPicker] = useState(false);

  // Queries
  const { data: routesData, isLoading: routesLoading } = useAllRoutes();
  const routes = routesData?.data ?? [];

  const { data: stepsData } = useRouteSteps(selectedRoute?.id ?? "");
  const steps = (stepsData?.data ?? []).sort((a, b) => a.sequence - b.sequence);

  const { data: assignmentsData } = useRouteProducts(selectedRoute?.id ?? "");
  const assignments = assignmentsData?.data ?? [];

  const { data: productsData } = useProducts();
  const allProducts = productsData?.data ?? [];

  // Build product lookup for displaying assigned product names
  const productMap = new Map<string, Product>(
    allProducts.map((p) => [p.id, p]),
  );

  // Products not yet assigned to the selected route
  const assignedIds = new Set(assignments.map((a) => a.product_id));
  const availableProducts = allProducts.filter((p) => !assignedIds.has(p.id));

  const assignMut = useAssignProductToRoute();
  const unassignMut = useUnassignProductFromRoute();

  if (routesLoading) {
    return <p className="text-sm text-gray-500 p-6">Loading…</p>;
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Route Editor</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Create and manage manufacturing routes, then assign products.
          </p>
        </div>
      </div>

      {/* Three-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left panel — Route list */}
        <div className="lg:col-span-1">
          <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">Routes</h2>
              <button
                onClick={() => setShowRouteForm(true)}
                className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
              >
                <PlusIcon className="h-3.5 w-3.5" />
                New
              </button>
            </div>
            <div className="divide-y divide-gray-100 max-h-[calc(100vh-220px)] overflow-y-auto">
              {routes.length === 0 && (
                <p className="px-4 py-6 text-center text-sm text-gray-400">
                  No routes defined yet.
                </p>
              )}
              {routes.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelectedRoute(r)}
                  className={`w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors ${
                    selectedRoute?.id === r.id ? "bg-indigo-50" : ""
                  }`}
                >
                  <div className="min-w-0">
                    <span className="text-sm font-medium text-gray-900 truncate block">
                      {r.name}
                    </span>
                    <span className="text-xs text-gray-500">v{r.version}</span>
                  </div>
                  <ChevronRightIcon className="h-4 w-4 text-gray-400 shrink-0" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Center panel — Steps table */}
        <div className="lg:col-span-2">
          {selectedRoute ? (
            <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-900">
                  Steps — {selectedRoute.name}
                </h2>
                <button
                  onClick={() => {
                    setEditingStep(null);
                    setShowStepForm(true);
                  }}
                  className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
                >
                  <PlusIcon className="h-3.5 w-3.5" />
                  New Step
                </button>
              </div>
              <div className="overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Seq
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Name
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Type
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Cycle Time
                      </th>
                      <th className="px-4 py-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {steps.map((s) => (
                      <tr
                        key={s.id}
                        className="hover:bg-gray-50 transition-colors"
                      >
                        <td className="px-4 py-2 text-sm font-mono text-gray-700">
                          {s.sequence}
                        </td>
                        <td className="px-4 py-2 text-sm font-medium text-gray-900">
                          {s.name}
                        </td>
                        <td className="px-4 py-2">
                          <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                            {s.step_type}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {s.expected_cycle_time_sec != null
                            ? `${s.expected_cycle_time_sec}s`
                            : "—"}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <button
                            onClick={() => {
                              setEditingStep(s);
                              setShowStepForm(true);
                            }}
                            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                            title="Edit step"
                          >
                            <PencilSquareIcon className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {steps.length === 0 && (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-4 py-6 text-center text-sm text-gray-400"
                        >
                          No steps defined. Click "New Step" to add one.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
              <p className="text-sm text-gray-400">
                Select a route to view and edit its steps.
              </p>
            </div>
          )}
        </div>

        {/* Right panel — Product assignments */}
        <div className="lg:col-span-1">
          {selectedRoute ? (
            <div className="rounded-lg border border-gray-200 bg-white shadow-sm sticky top-6">
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-900">
                  Products
                </h2>
                <button
                  onClick={() => setShowProductPicker(!showProductPicker)}
                  className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
                >
                  <PlusIcon className="h-3.5 w-3.5" />
                  Assign
                </button>
              </div>

              {/* Inline product picker */}
              {showProductPicker && (
                <div className="border-b border-gray-200 px-4 py-3 bg-gray-50">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Select product to assign
                  </label>
                  {availableProducts.length === 0 ? (
                    <p className="text-xs text-gray-400">All products already assigned.</p>
                  ) : (
                    <div className="max-h-40 overflow-y-auto space-y-1">
                      {availableProducts.map((p) => (
                        <button
                          key={p.id}
                          onClick={async () => {
                            await assignMut.mutateAsync({
                              routeId: selectedRoute.id,
                              product_id: p.id,
                            });
                            setShowProductPicker(false);
                          }}
                          className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-indigo-50 transition-colors"
                        >
                          <span className="font-medium text-gray-900">{p.code}</span>
                          <span className="ml-2 text-gray-500">{p.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Assigned products list */}
              <div className="divide-y divide-gray-100">
                {assignments.length === 0 && (
                  <p className="px-4 py-6 text-center text-sm text-gray-400">
                    No products assigned.
                  </p>
                )}
                {assignments.map((a) => {
                  const product = productMap.get(a.product_id);
                  return (
                    <div
                      key={a.id}
                      className="px-4 py-2.5 flex items-center justify-between"
                    >
                      <div className="min-w-0">
                        <span className="text-sm font-medium text-gray-900 truncate block">
                          {product?.code ?? a.product_id.slice(0, 8)}
                        </span>
                        <span className="text-xs text-gray-500 truncate block">
                          {product?.name ?? ""}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          if (confirm(`Remove ${product?.code ?? "this product"} from route?`)) {
                            unassignMut.mutate({
                              routeId: selectedRoute.id,
                              productId: a.product_id,
                            });
                          }
                        }}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Remove assignment"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center">
              <p className="text-sm text-gray-400">
                Select a route to manage product assignments.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Dialogs */}
      {showRouteForm && (
        <RouteCreateDialog
          onClose={() => setShowRouteForm(false)}
        />
      )}
      {showStepForm && selectedRoute && (
        <StepFormDialog
          routeId={selectedRoute.id}
          step={editingStep}
          onClose={() => {
            setShowStepForm(false);
            setEditingStep(null);
          }}
        />
      )}
    </div>
  );
}
