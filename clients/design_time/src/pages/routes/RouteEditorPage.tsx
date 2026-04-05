/**
 * Route Editor Page — standalone manufacturing route editor.
 * URL: /routes
 *
 * Three-panel layout:
 *   Left:   route list + create/edit/delete
 *   Center: steps table for the selected route (create/edit/delete)
 *   Right:  material assignments for the selected route
 */

import { useState } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  useAllRoutes,
  useRouteSteps,
  useRouteMaterials,
  useDeleteRoute,
  useDeleteStep,
  useAssignMaterialToRoute,
  useUnassignMaterialFromRoute,
} from "../../hooks/useProductDef";
import { useMaterials } from "../../hooks/useMaterial";
import type { ProcessRoute, RouteStep, Material } from "../../types";
import RouteFormDialog from "./RouteFormDialog";
import StepFormDialog from "../products/StepFormDialog";

export default function RouteEditorPage() {
  const [selectedRoute, setSelectedRoute] = useState<ProcessRoute | null>(null);
  const [showRouteForm, setShowRouteForm] = useState(false);
  const [editingRoute, setEditingRoute] = useState<ProcessRoute | null>(null);
  const [showStepForm, setShowStepForm] = useState(false);
  const [editingStep, setEditingStep] = useState<RouteStep | null>(null);
  const [showMaterialPicker, setShowMaterialPicker] = useState(false);

  // Queries
  const { data: routesData, isLoading: routesLoading } = useAllRoutes();
  const routes = routesData?.data ?? [];

  const { data: stepsData } = useRouteSteps(selectedRoute?.id ?? "");
  const steps = (stepsData?.data ?? []).sort((a, b) => a.sequence - b.sequence);

  const { data: materialAssignmentsData } = useRouteMaterials(selectedRoute?.id ?? "");
  const materialAssignments = materialAssignmentsData?.data ?? [];

  const { data: materialsData } = useMaterials();
  const allMaterials = materialsData?.data ?? [];

  // Build material lookup for displaying assigned material names
  const materialMap = new Map<string, Material>(
    allMaterials.map((m) => [m.id, m]),
  );

  // Materials not yet assigned to the selected route
  const assignedMaterialIds = new Set(materialAssignments.map((a) => a.material_id));
  const availableMaterials = allMaterials.filter((m) => !assignedMaterialIds.has(m.id));

  const deleteRouteMut = useDeleteRoute();
  const deleteStepMut = useDeleteStep();
  const assignMaterialMut = useAssignMaterialToRoute();
  const unassignMaterialMut = useUnassignMaterialFromRoute();

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
                <div className="border-b border-gray-200 px-4 py-3 bg-gray-50">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Select material to assign
                  </label>
                  {availableMaterials.length === 0 ? (
                    <p className="text-xs text-gray-400">All materials already assigned.</p>
                  ) : (
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {availableMaterials.map((m) => (
                        <button
                          key={m.id}
                          onClick={async () => {
                            await assignMaterialMut.mutateAsync({
                              routeId: selectedRoute.id,
                              material_id: m.id,
                            });
                            setShowMaterialPicker(false);
                          }}
                          className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-indigo-50 transition-colors"
                        >
                          <span className="font-medium text-gray-900">{m.code}</span>
                          <span className="ml-2 text-gray-500">{m.name}</span>
                          <span className="ml-1 inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                            {m.material_type}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Assigned materials list */}
              <div className="divide-y divide-gray-100">
                {materialAssignments.length === 0 && (
                  <p className="px-4 py-6 text-center text-sm text-gray-400">
                    No materials assigned.
                  </p>
                )}
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
