/**
 * Route Editor Page — standalone manufacturing route editor.
 * URL: /routes
 *
 * Three-panel layout:
 *   Left:   route list + create/edit/delete
 *   Center: steps table for the selected route (create/edit/delete)
 *   Right:  material assignments for the selected route
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  useAllRoutes,
  useProducts,
  useRouteSteps,
  useRouteMaterials,
  useRouteProducts,
  useDeleteRoute,
  useDeleteStep,
  useAssignMaterialToRoute,
  useUnassignMaterialFromRoute,
  useAssignProductToRoute,
  useUnassignProductFromRoute,
} from "../../hooks/useProductDef";
import { useMaterials } from "../../hooks/useMaterial";
import { useAllWorkCells, useEquipmentClasses, useAllEquipment } from "../../hooks/usePhysicalModel";
import type { ProcessRoute, RouteStep, Material, Product } from "../../types";
import RouteFormDialog from "./RouteFormDialog";
import StepFormDialog from "../products/StepFormDialog";
import StepEquipReqCountBadge from "../products/StepEquipReqCountBadge";
import RouteFlowDiagram from "./RouteFlowDiagram";

const PRODUCT_TYPES = ["discrete", "process", "semi_finished", "configurable"] as const;
const MATERIAL_TYPES = ["raw", "intermediate", "finished", "semi", "consumable", "packaging", "spare"] as const;

export default function RouteEditorPage() {
  const [selectedRoute, setSelectedRoute] = useState<ProcessRoute | null>(null);
  const [showRouteForm, setShowRouteForm] = useState(false);
  const [editingRoute, setEditingRoute] = useState<ProcessRoute | null>(null);
  const [showStepForm, setShowStepForm] = useState(false);
  const [editingStep, setEditingStep] = useState<RouteStep | null>(null);
  const [showMaterialPicker, setShowMaterialPicker] = useState(false);
  const [pickerSource, setPickerSource] = useState<"materials" | "products">("materials");
  const [pickerTypeFilter, setPickerTypeFilter] = useState("");
  const [stepsView, setStepsView] = useState<"table" | "diagram">("table");

  // Queries
  const { data: routesData, isLoading: routesLoading } = useAllRoutes();
  const routes = routesData?.data ?? [];

  const { data: productsData } = useProducts();
  const allProducts = productsData?.data ?? [];

  const { data: stepsData } = useRouteSteps(selectedRoute?.id ?? "");
  const steps = (stepsData?.data ?? []).sort((a, b) => a.sequence - b.sequence);

  const { data: materialAssignmentsData } = useRouteMaterials(selectedRoute?.id ?? "");
  const materialAssignments = materialAssignmentsData?.data ?? [];

  const { data: productAssignmentsData } = useRouteProducts(selectedRoute?.id ?? "");
  const productAssignments = productAssignmentsData?.data ?? [];

  const { data: materialsData } = useMaterials();
  const allMaterials = materialsData?.data ?? [];

  const { data: wcData } = useAllWorkCells();
  const allWorkCells = wcData?.data ?? [];
  const wcMap = new Map(allWorkCells.map((wc) => [wc.id, wc]));

  const { data: ecData } = useEquipmentClasses();
  const allEquipmentClasses = ecData?.data ?? [];
  const ecMap = new Map(allEquipmentClasses.map((ec: { id: string; code: string }) => [ec.id, ec]));

  // Derive a work-cell map keyed by equipment class, via the equipment roster.
  // ProcessSegment has no direct work_cell_id (ISA-95 models equipment-class
  // requirements at the step level), so we surface the work cells that host
  // equipment of the step's required class.
  const { data: equipData } = useAllEquipment();
  const allEquipment = equipData?.data ?? [];
  const classToWorkCells = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const e of allEquipment) {
      if (!e.equipment_class_id) continue;
      const set = map.get(e.equipment_class_id) ?? new Set<string>();
      set.add(e.work_cell_id);
      map.set(e.equipment_class_id, set);
    }
    return map;
  }, [allEquipment]);

  // Build material lookup for displaying assigned material names
  const materialMap = new Map<string, Material>(
    allMaterials.map((m) => [m.id, m]),
  );

  // Build product lookup for displaying assigned product names
  const productMap = new Map<string, Product>(
    allProducts.map((p) => [p.id, p]),
  );

  // Materials not yet assigned to the selected route
  const assignedMaterialIds = new Set(materialAssignments.map((a) => a.material_id));
  const availableMaterials = allMaterials.filter((m) => !assignedMaterialIds.has(m.id));

  // Products not yet assigned to the selected route
  const assignedProductIds = new Set(productAssignments.map((a) => a.product_id));
  const availableProducts = allProducts.filter((p) => !assignedProductIds.has(p.id));

  // Filtered picker items based on radio + type dropdown
  const filteredPickerItems = useMemo(() => {
    if (pickerSource === "products") {
      return availableProducts
        .filter((p) => !pickerTypeFilter || p.product_type === pickerTypeFilter)
        .map((p) => ({ id: p.id, code: p.code, name: p.name, type: p.product_type }));
    }
    return availableMaterials
      .filter((m) => !pickerTypeFilter || m.material_type === pickerTypeFilter)
      .map((m) => ({ id: m.id, code: m.code, name: m.name, type: m.material_type }));
  }, [pickerSource, pickerTypeFilter, availableProducts, availableMaterials]);

  const deleteRouteMut = useDeleteRoute();
  const deleteStepMut = useDeleteStep();
  const assignMaterialMut = useAssignMaterialToRoute();
  const unassignMaterialMut = useUnassignMaterialFromRoute();
  const assignProductMut = useAssignProductToRoute();
  const unassignProductMut = useUnassignProductFromRoute();

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
            Create and manage manufacturing routes, steps, and material assignments.
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
                onClick={() => {
                  setEditingRoute(null);
                  setShowRouteForm(true);
                }}
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
                <div
                  key={r.id}
                  className={`flex items-center justify-between hover:bg-gray-50 transition-colors ${
                    selectedRoute?.id === r.id ? "bg-indigo-50" : ""
                  }`}
                >
                  <button
                    onClick={() => setSelectedRoute(r)}
                    className="flex-1 text-left px-4 py-3 min-w-0"
                  >
                    <span className="text-sm font-medium text-gray-900 truncate block">
                      {r.name}
                    </span>
                    <span className="text-xs text-gray-500">v{r.version}</span>
                  </button>
                  <div className="flex items-center gap-0.5 pr-2 shrink-0">
                    <button
                      onClick={() => {
                        setEditingRoute(r);
                        setShowRouteForm(true);
                      }}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                      title="Edit route"
                    >
                      <PencilSquareIcon className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete route "${r.name}"?`)) {
                          deleteRouteMut.mutate(r.id);
                          if (selectedRoute?.id === r.id) setSelectedRoute(null);
                        }
                      }}
                      className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      title="Delete route"
                    >
                      <TrashIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
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
                <div className="flex items-center gap-2">
                  <div className="inline-flex rounded-md border border-gray-300 bg-white p-0.5 text-xs">
                    <button
                      type="button"
                      onClick={() => setStepsView("table")}
                      className={`rounded px-2 py-1 font-medium transition-colors ${
                        stepsView === "table"
                          ? "bg-indigo-600 text-white"
                          : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      Table
                    </button>
                    <button
                      type="button"
                      onClick={() => setStepsView("diagram")}
                      className={`rounded px-2 py-1 font-medium transition-colors ${
                        stepsView === "diagram"
                          ? "bg-indigo-600 text-white"
                          : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      Diagram
                    </button>
                  </div>
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
              </div>
              {stepsView === "diagram" ? (
                <RouteFlowDiagram steps={steps} />
              ) : (
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
                        Equipment Class
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                        Work Cell
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
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {s.equipment_class_id ? (ecMap.get(s.equipment_class_id)?.code ?? "—") : "—"}
                          <StepEquipReqCountBadge stepId={s.id} />
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {(() => {
                            if (s.work_cell_id) {
                              return wcMap.get(s.work_cell_id)?.code ?? "—";
                            }
                            if (s.equipment_class_id) {
                              const cellIds = classToWorkCells.get(s.equipment_class_id);
                              if (cellIds && cellIds.size > 0) {
                                const codes = Array.from(cellIds)
                                  .map((id) => wcMap.get(id)?.code)
                                  .filter(Boolean);
                                if (codes.length > 0) return codes.join(", ");
                              }
                            }
                            return "—";
                          })()}
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
                          <div className="inline-flex items-center gap-0.5">
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
                            <button
                              onClick={() => {
                                if (confirm(`Delete step "${s.name}"?`)) {
                                  deleteStepMut.mutate(s.id);
                                }
                              }}
                              className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                              title="Delete step"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
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
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
              <p className="text-sm text-gray-400">
                Select a route to view and edit its steps.
              </p>
            </div>
          )}
        </div>

        {/* Right panel — Material assignments */}
        <div className="lg:col-span-1">
          {selectedRoute ? (
            <div className="rounded-lg border border-gray-200 bg-white shadow-sm sticky top-6">
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-900">
                  Materials
                </h2>
                <button
                  onClick={() => setShowMaterialPicker(!showMaterialPicker)}
                  className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
                >
                  <PlusIcon className="h-3.5 w-3.5" />
                  Assign
                </button>
              </div>

              {/* Inline material picker */}
              {showMaterialPicker && (
                <div className="border-b border-gray-200 px-4 py-3 bg-gray-50 space-y-2">
                  {/* Radio: Products vs Materials */}
                  <div className="flex items-center gap-4">
                    <label className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 cursor-pointer">
                      <input
                        type="radio"
                        name="pickerSource"
                        checked={pickerSource === "materials"}
                        onChange={() => { setPickerSource("materials"); setPickerTypeFilter(""); }}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      Materials
                    </label>
                    <label className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 cursor-pointer">
                      <input
                        type="radio"
                        name="pickerSource"
                        checked={pickerSource === "products"}
                        onChange={() => { setPickerSource("products"); setPickerTypeFilter(""); }}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      Products
                    </label>
                  </div>

                  {/* Type dropdown */}
                  <select
                    value={pickerTypeFilter}
                    onChange={(e) => setPickerTypeFilter(e.target.value)}
                    className="block w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="">All types</option>
                    {(pickerSource === "products" ? PRODUCT_TYPES : MATERIAL_TYPES).map((t) => (
                      <option key={t} value={t}>
                        {t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </option>
                    ))}
                  </select>

                  {/* Filtered list */}
                  {filteredPickerItems.length === 0 ? (
                    <p className="text-xs text-gray-400">
                      {pickerSource === "materials" ? "All materials already assigned." : "All products already assigned."}
                    </p>
                  ) : (
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {filteredPickerItems.map((item) => (
                        <button
                          key={item.id}
                          onClick={async () => {
                            if (pickerSource === "products") {
                              await assignProductMut.mutateAsync({
                                routeId: selectedRoute.id,
                                product_id: item.id,
                              });
                            } else {
                              await assignMaterialMut.mutateAsync({
                                routeId: selectedRoute.id,
                                material_id: item.id,
                              });
                            }
                            setShowMaterialPicker(false);
                          }}
                          className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-indigo-50 transition-colors"
                        >
                          <span className="font-medium text-gray-900">{item.code}</span>
                          <span className="ml-2 text-gray-500">{item.name}</span>
                          <span className="ml-1 inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                            {item.type}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Assigned items list */}
              <div className="divide-y divide-gray-100">
                {materialAssignments.length === 0 && productAssignments.length === 0 && (
                  <p className="px-4 py-6 text-center text-sm text-gray-400">
                    No materials or products assigned.
                  </p>
                )}
                {productAssignments.map((a) => {
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
                          {product?.product_type && (
                            <span className="ml-1 inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-xs text-indigo-600">
                              {product.product_type}
                            </span>
                          )}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          if (confirm(`Remove ${product?.code ?? "this product"} from route?`)) {
                            unassignProductMut.mutate({
                              routeId: selectedRoute.id,
                              productId: a.product_id,
                            });
                          }
                        }}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Remove assignment"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })}
                {materialAssignments.map((a) => {
                  const material = materialMap.get(a.material_id);
                  return (
                    <div
                      key={a.id}
                      className="px-4 py-2.5 flex items-center justify-between"
                    >
                      <div className="min-w-0">
                        <span className="text-sm font-medium text-gray-900 truncate block">
                          {material?.code ?? a.material_id.slice(0, 8)}
                        </span>
                        <span className="text-xs text-gray-500 truncate block">
                          {material?.name ?? ""}
                          {material?.material_type && (
                            <span className="ml-1 inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                              {material.material_type}
                            </span>
                          )}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          if (confirm(`Remove ${material?.code ?? "this material"} from route?`)) {
                            unassignMaterialMut.mutate({
                              routeId: selectedRoute.id,
                              materialId: a.material_id,
                            });
                          }
                        }}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Remove assignment"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
              <p className="text-sm text-gray-400">
                Select a route to manage material assignments.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Dialogs */}
      {showRouteForm && (
        <RouteFormDialog
          route={editingRoute}
          onClose={() => {
            setShowRouteForm(false);
            setEditingRoute(null);
          }}
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
