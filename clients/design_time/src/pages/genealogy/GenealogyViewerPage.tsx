/**
 * GenealogyViewerPage — look up full traceability record by unit or lot ID.
 */

import { useState } from "react";
import {
  MagnifyingGlassIcon,
  ChevronDownIcon,
} from "@heroicons/react/24/outline";
import { useUnitGenealogy, useLotGenealogy } from "../../hooks/useGenealogy";
import type {
  GenealogyRecord,
  GenealogyStepRecord,
  GenealogyMaterialRecord,
  GenealogyTestRecord,
  GenealogyDataRecord,
} from "../../types/genealogy";

type LookupMode = "unit" | "lot";

export default function GenealogyViewerPage() {
  const [mode, setMode] = useState<LookupMode>("unit");
  const [inputId, setInputId] = useState("");
  const [searchId, setSearchId] = useState("");

  const unitQuery = useUnitGenealogy(
    mode === "unit" ? searchId : "",
    mode === "unit" && searchId.length > 0,
  );
  const lotQuery = useLotGenealogy(
    mode === "lot" ? searchId : "",
    mode === "lot" && searchId.length > 0,
  );

  const isLoading =
    (mode === "unit" && unitQuery.isLoading) ||
    (mode === "lot" && lotQuery.isLoading);
  const error =
    (mode === "unit" && unitQuery.error) ||
    (mode === "lot" && lotQuery.error);
  const record: GenealogyRecord | undefined =
    mode === "unit" ? unitQuery.data : lotQuery.data;

  const handleSearch = () => {
    if (inputId.trim()) setSearchId(inputId.trim());
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Genealogy Viewer</h1>
        <p className="text-sm text-gray-500 mt-1">
          Look up full traceability records by unit or lot.
        </p>
      </div>

      {/* Search bar */}
      <div className="flex items-end gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Mode
          </label>
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value as LookupMode);
              setSearchId("");
            }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            <option value="unit">Unit</option>
            <option value="lot">Lot</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {mode === "unit" ? "Unit ID" : "Lot ID"}
          </label>
          <input
            value={inputId}
            onChange={(e) => setInputId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder={`Enter ${mode} identifier…`}
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <button
          onClick={handleSearch}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <MagnifyingGlassIcon className="h-4 w-4" />
          Search
        </button>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading genealogy…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load genealogy record. Check the ID and try again.
        </div>
      )}

      {/* Results */}
      {record && !isLoading && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Record for {mode === "unit" ? "Unit" : "Lot"}: {searchId}
            </h2>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              <dt className="text-gray-500">Unit ID</dt>
              <dd className="font-mono text-gray-900">
                {record.unit_id ?? "—"}
              </dd>
              <dt className="text-gray-500">Lot ID</dt>
              <dd className="font-mono text-gray-900">
                {record.lot_id ?? "—"}
              </dd>
              <dt className="text-gray-500">Order ID</dt>
              <dd className="font-mono text-gray-900">
                {record.order_id ?? "—"}
              </dd>
              <dt className="text-gray-500">Product</dt>
              <dd className="font-mono text-gray-900">
                {record.product_id ?? "—"}
              </dd>
            </dl>
          </div>

          {/* Steps */}
          <CollapsibleSection
            title="Steps"
            count={record.steps?.length ?? 0}
          >
            {(record.steps ?? []).map((s: GenealogyStepRecord, i: number) => (
              <div
                key={i}
                className="rounded border border-gray-100 bg-gray-50 p-3 text-sm"
              >
                <p>
                  <span className="font-medium text-gray-700">Step:</span>{" "}
                  {s.step_id}
                </p>
                <p>
                  <span className="font-medium text-gray-700">Equipment:</span>{" "}
                  {s.equipment_id ?? "—"}
                </p>
                <p>
                  <span className="font-medium text-gray-700">Entered:</span>{" "}
                  {s.entered_at ? new Date(s.entered_at).toLocaleString() : "—"}
                </p>
                <p>
                  <span className="font-medium text-gray-700">Exited:</span>{" "}
                  {s.exited_at
                    ? new Date(s.exited_at).toLocaleString()
                    : "—"}
                </p>
              </div>
            ))}
          </CollapsibleSection>

          {/* Materials */}
          <CollapsibleSection
            title="Materials Consumed"
            count={record.materials?.length ?? 0}
          >
            {(record.materials ?? []).map(
              (m: GenealogyMaterialRecord, i: number) => (
                <div
                  key={i}
                  className="rounded border border-gray-100 bg-gray-50 p-3 text-sm"
                >
                  <p>
                    <span className="font-medium text-gray-700">
                      Material:
                    </span>{" "}
                    {m.material_code ?? m.material_lot_id}
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">Lot #:</span>{" "}
                    {m.lot_number ?? "—"}
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">Qty:</span>{" "}
                    {m.quantity_consumed}
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">Step:</span>{" "}
                    {m.step_id ?? "—"}
                  </p>
                </div>
              ),
            )}
          </CollapsibleSection>

          {/* Test Results */}
          <CollapsibleSection
            title="Test Results"
            count={record.test_results?.length ?? 0}
          >
            {(record.test_results ?? []).map(
              (t: GenealogyTestRecord, i: number) => (
                <div
                  key={i}
                  className="rounded border border-gray-100 bg-gray-50 p-3 text-sm"
                >
                  <p>
                    <span className="font-medium text-gray-700">Test:</span>{" "}
                    {t.test_code ?? t.result_id}
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">Result:</span>{" "}
                    <span
                      className={
                        t.result === "pass"
                          ? "text-green-700"
                          : t.result === "fail"
                          ? "text-red-600"
                          : "text-gray-600"
                      }
                    >
                      {t.result}
                    </span>
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">Tested:</span>{" "}
                    {t.tested_at
                      ? new Date(t.tested_at).toLocaleString()
                      : "—"}
                  </p>
                </div>
              ),
            )}
          </CollapsibleSection>

          {/* Data Points */}
          <CollapsibleSection
            title="Data Points"
            count={record.data_points?.length ?? 0}
          >
            {(record.data_points ?? []).map(
              (d: GenealogyDataRecord, i: number) => (
                <div
                  key={i}
                  className="rounded border border-gray-100 bg-gray-50 p-3 text-sm"
                >
                  <p>
                    <span className="font-medium text-gray-700">
                      Parameter:
                    </span>{" "}
                    {d.definition_code ?? d.data_point_id}
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">Value:</span>{" "}
                    {d.value_numeric ?? d.value_string ?? (d.value_boolean != null ? String(d.value_boolean) : "—")}
                  </p>
                  <p>
                    <span className="font-medium text-gray-700">
                      Collected:
                    </span>{" "}
                    {d.collected_at
                      ? new Date(d.collected_at).toLocaleString()
                      : "—"}
                  </p>
                </div>
              ),
            )}
          </CollapsibleSection>
        </div>
      )}

      {/* Empty state */}
      {!record && !isLoading && !error && searchId && (
        <div className="py-12 text-center text-sm text-gray-400">
          No genealogy record found for {mode} "{searchId}".
        </div>
      )}
    </div>
  );
}

/* ─── Collapsible helper ──────────────────────────────────────── */

function CollapsibleSection({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-sm font-semibold text-gray-800">
          {title}{" "}
          <span className="ml-1 text-gray-400 font-normal">({count})</span>
        </span>
        <ChevronDownIcon
          className={`h-4 w-4 text-gray-400 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && count > 0 && (
        <div className="border-t border-gray-100 p-4 space-y-2">
          {children}
        </div>
      )}
      {open && count === 0 && (
        <div className="border-t border-gray-100 px-4 py-6 text-center text-sm text-gray-400">
          No {title.toLowerCase()} recorded.
        </div>
      )}
    </div>
  );
}
