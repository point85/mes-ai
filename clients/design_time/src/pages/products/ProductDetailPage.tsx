/**
 * Product Detail Page — routes, steps, and step dispositions editor.
 * URL: /products/:productId
 */

import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  PlusIcon,
  PencilSquareIcon,
  ChevronRightIcon,
  ArrowLeftIcon,
} from "@heroicons/react/24/outline";
import {
  useRoutes,
  useRouteSteps,
  useBOMs,
  useBOMItems,
} from "../../hooks/useProductDef";
import { fetchProduct } from "../../api/productDef";
import { useQuery } from "@tanstack/react-query";
import type {
  ProcessRoute,
  RouteStep,
  BOMItem,
} from "../../types";
import RouteFormDialog from "./RouteFormDialog";
import StepFormDialog from "./StepFormDialog";
import StepEquipReqCountBadge from "./StepEquipReqCountBadge";

export default function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const [selectedRoute, setSelectedRoute] = useState<ProcessRoute | null>(null);
  const [selectedStep, setSelectedStep] = useState<RouteStep | null>(null);

  // Dialogs
  const [showRouteForm, setShowRouteForm] = useState(false);
  const [showStepForm, setShowStepForm] = useState(false);
  const [editingStep, setEditingStep] = useState<RouteStep | null>(null);

  // Queries
  const { data: product, isLoading: productLoading } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => fetchProduct(productId!),
    enabled: !!productId,
  });
  const { data: routesData } = useRoutes(productId ?? "");
  const routes = routesData?.data ?? [];

  const { data: stepsData } = useRouteSteps(selectedRoute?.id ?? "");
  const steps = (stepsData?.data ?? []).sort((a, b) => a.sequence - b.sequence);

  // BOM items for step-material display
  const { data: bomsData } = useBOMs(productId ?? "");
  const boms = bomsData?.data ?? [];
  const defaultBomId = boms.length > 0 ? boms[0].id : "";
  const { data: bomItemsData } = useBOMItems(defaultBomId);
  const bomItems = bomItemsData?.data ?? [];

  // Group BOM items by process_segment_id for quick lookup
  const stepMaterialsMap = new Map<string, BOMItem[]>();
  for (const item of bomItems) {
    if (item.process_segment_id) {
      const list = stepMaterialsMap.get(item.process_segment_id) ?? [];
      list.push(item);
      stepMaterialsMap.set(item.process_segment_id, list);
    }
  }

  if (productLoading) {
    return <p className="text-sm text-gray-500 p-6">Loading…</p>;
  }
  if (!product) {
    return <p className="text-sm text-red-600 p-6">Product not found.</p>;
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb / back */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link
          to="/products"
          className="flex items-center gap-1 hover:text-indigo-600 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Products
        </Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="font-medium text-gray-900">
          {product.code} — {product.name}
        </span>
      </div>

      {/* Product header */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{product.name}</h1>
            <p className="mt-0.5 text-sm text-gray-500">
              {product.code} · v{product.version} · {product.product_type} · {product.uom_symbol}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/products/${productId}/boms`}
              className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
            >
              Manage BOMs
            </Link>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                product.is_active
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {product.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
      </div>

      {/* Two-column layout: Routes & Steps | Transitions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel — Routes & Steps */}
        <div className="lg:col-span-2 space-y-6">
          {/* Routes section */}
          <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">
                Process Routes
              </h2>
              <button
                onClick={() => setShowRouteForm(true)}
                className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
              >
                <PlusIcon className="h-3.5 w-3.5" />
                New Route
              </button>
            </div>
            <div className="divide-y divide-gray-100">
              {routes.length === 0 && (
                <p className="px-4 py-6 text-center text-sm text-gray-400">
                  No routes defined yet.
                </p>
              )}
              {routes.map((r) => (
                <button
                  key={r.id}
                  onClick={() => {
                    setSelectedRoute(r);
                    setSelectedStep(null);
                  }}
                  className={`w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors ${
                    selectedRoute?.id === r.id ? "bg-indigo-50" : ""
                  }`}
                >
                  <div>
                    <span className="text-sm font-medium text-gray-900">
                      {r.name}
                    </span>
                    <span className="ml-2 text-xs text-gray-500">v{r.version}</span>
                    {r.is_default && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
                        default
                      </span>
                    )}
                  </div>
                  <ChevronRightIcon className="h-4 w-4 text-gray-400" />
                </button>
              ))}
            </div>
          </div>

          {/* Steps section */}
          {selectedRoute && (
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
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Inputs
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Outputs
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Consumed Materials
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
                        onClick={() => setSelectedStep(s)}
                        className={`cursor-pointer hover:bg-gray-50 transition-colors ${
                          selectedStep?.id === s.id ? "bg-indigo-50" : ""
                        }`}
                      >
                        <td className="px-4 py-2 text-sm font-mono text-gray-700">
                          {s.sequence}
                        </td>
                        <td className="px-4 py-2 text-sm font-medium text-gray-900">
                          {s.name}
                          <StepEquipReqCountBadge stepId={s.id} />
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
                        <td className="px-4 py-2">
                          {(s.input_dispositions ?? []).length === 0 ? (
                            <span className="text-xs text-gray-400">—</span>
                          ) : (
                            <div className="flex flex-wrap gap-1">
                              {s.input_dispositions.map((d) => (
                                <span
                                  key={d.id}
                                  className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 font-mono text-[10px] text-blue-700"
                                  title={d.name}
                                >
                                  {d.code}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-2">
                          {(s.output_dispositions ?? []).length === 0 ? (
                            <span className="text-xs text-gray-400">—</span>
                          ) : (
                            <div className="flex flex-wrap gap-1">
                              {s.output_dispositions.map((d) => (
                                <span
                                  key={d.id}
                                  className="inline-flex items-center rounded bg-emerald-50 px-1.5 py-0.5 font-mono text-[10px] text-emerald-700"
                                  title={d.name}
                                >
                                  {d.code}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-2">
                          {(stepMaterialsMap.get(s.id) ?? []).length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {stepMaterialsMap.get(s.id)!.map((item) => (
                                <span
                                  key={item.id}
                                  className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20"
                                  title={`${item.quantity} ${item.uom_symbol}`}
                                >
                                  {item.material_code} ({item.quantity} {item.uom_symbol})
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
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
                          colSpan={7}
                          className="px-4 py-6 text-center text-sm text-gray-400"
                        >
                          No steps defined yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Right panel — Step Detail */}
        <div className="lg:col-span-1">
          {selectedStep ? (
            <div className="rounded-lg border border-gray-200 bg-white shadow-sm sticky top-6">
              <div className="border-b border-gray-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-900">Step Detail</h2>
                <p className="mt-1 text-xs text-gray-500">
                  <span className="font-medium">{selectedStep.sequence}. {selectedStep.name}</span>
                  {selectedStep.is_initial_step && (
                    <span className="ml-2 inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
                      initial
                    </span>
                  )}
                </p>
              </div>
              <div className="divide-y divide-gray-100 p-4 space-y-4">
                {/* Input Dispositions */}
                <div>
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    Input Dispositions
                    <span className="ml-1 text-gray-400 font-normal">(WIP routed in by)</span>
                  </p>
                  {(selectedStep.input_dispositions ?? []).length === 0 ? (
                    <p className="text-xs italic text-gray-400">
                      {selectedStep.is_initial_step ? "Entry point — no input dispositions needed" : "None"}
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {selectedStep.input_dispositions.map((d) => (
                        <span
                          key={d.id}
                          className="inline-flex items-center rounded bg-blue-50 px-2 py-0.5 text-xs font-mono text-blue-700 ring-1 ring-inset ring-blue-600/20"
                          title={d.name}
                        >
                          {d.code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {/* Output Dispositions */}
                <div>
                  <p className="text-xs font-semibold text-gray-700 mb-1">
                    Output Dispositions
                    <span className="ml-1 text-gray-400 font-normal">(WIP routed out by)</span>
                  </p>
                  {(selectedStep.output_dispositions ?? []).length === 0 ? (
                    <p className="text-xs italic text-gray-400">Terminal — WIP completes here</p>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {selectedStep.output_dispositions.map((d) => (
                        <span
                          key={d.id}
                          className="inline-flex items-center rounded bg-emerald-50 px-2 py-0.5 text-xs font-mono text-emerald-700 ring-1 ring-inset ring-emerald-600/20"
                          title={d.name}
                        >
                          {d.code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {/* Routing hint */}
                <div className="rounded bg-gray-50 px-3 py-2 text-xs text-gray-500">
                  {(selectedStep.output_dispositions ?? []).length === 0 && (
                    <p>0 outputs → <strong>terminal step</strong>. WIP is completed here.</p>
                  )}
                  {(selectedStep.output_dispositions ?? []).length === 1 && (
                    <p>1 output → <strong>auto-routed</strong>. No operator disposition pick needed.</p>
                  )}
                  {(selectedStep.output_dispositions ?? []).length > 1 && (
                    <p>{selectedStep.output_dispositions.length} outputs → <strong>operator picks</strong> a disposition at completion.</p>
                  )}
                </div>
                <div className="pt-1">
                  <button
                    onClick={() => {
                      setEditingStep(selectedStep);
                      setShowStepForm(true);
                    }}
                    className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
                  >
                    <PencilSquareIcon className="h-3.5 w-3.5" />
                    Edit Step
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center">
              <p className="text-sm text-gray-400">
                {selectedRoute
                  ? "Select a step to view its dispositions."
                  : "Select a route, then a step to see details."}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Dialogs */}
      {showRouteForm && (
        <RouteFormDialog
          productId={productId!}
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
