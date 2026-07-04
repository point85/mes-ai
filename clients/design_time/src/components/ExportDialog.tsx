/**
 * ExportDialog — select DT objects to export as a zip archive of JSON files.
 *
 * Tree layout:
 *   ☐ All
 *     ☐ Sites                (hierarchical — selecting a site exports its entire subtree)
 *       ☐ APEX-ELEC
 *     ☐ Equipment Classes
 *       ☐ Mixer
 *     ☐ Storage Locations    (flat)
 *     ☐ Products             (flat, includes BOMs)
 *     ☐ Routes               (flat, includes steps)
 *     ☐ Dispositions         (flat)
 *     ☐ Materials            (flat)
 *     ☐ Units of Measure     (flat)
 *     ☐ Work Schedules       (flat, includes full detail)
 *     ☐ Data Definitions     (flat)
 *     ☐ Reason Codes         (hierarchical — selecting a reason exports its entire subtree)
 */

import {
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
  XMarkIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ArrowDownTrayIcon,
} from "@heroicons/react/24/outline";
import {
  fetchSites,
  fetchEquipmentClasses,
  fetchStorageLocations,
  fetchProducts,
  fetchAllRoutes,
  fetchDispositions,
  fetchMaterials,
  fetchUoMs,
  fetchWorkSchedules,
  fetchDataDefinitions,
  fetchReasons,
} from "../api";
import { buildExportZip, type ExportSelection } from "../utils/exportUtils";

// ─── Types ──────────────────────────────────────────────────────────────────

type ExportCategory =
  | "sites"
  | "equipment_classes"
  | "storage_locations"
  | "products"
  | "routes"
  | "dispositions"
  | "materials"
  | "uom"
  | "work_schedules"
  | "data_definitions"
  | "reason_codes";

interface EntityItem {
  id: string;
  label: string;
}

interface CategoryConfig {
  key: ExportCategory;
  label: string;
  items: EntityItem[];
}

type CheckState = "checked" | "indeterminate" | "unchecked";

// ─── Props ───────────────────────────────────────────────────────────────────

interface Props {
  onClose: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function itemKey(category: ExportCategory, id: string): string {
  return `${category}:${id}`;
}

function getCheckState(
  relevant: string[],
  selected: Set<string>,
): CheckState {
  if (relevant.length === 0) return "unchecked";
  const selectedCount = relevant.filter((k) => selected.has(k)).length;
  if (selectedCount === 0) return "unchecked";
  if (selectedCount === relevant.length) return "checked";
  return "indeterminate";
}

// ─── Indeterminate checkbox helper ───────────────────────────────────────────

interface CheckboxProps {
  state: CheckState;
  onChange: () => void;
  id?: string;
  label?: string;
  disabled?: boolean;
}

function Checkbox({ state, onChange, id, label, disabled }: CheckboxProps) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.checked = state === "checked";
      ref.current.indeterminate = state === "indeterminate";
    }
  }, [state]);

  return (
    <input
      ref={ref}
      id={id}
      type="checkbox"
      disabled={disabled}
      onChange={onChange}
      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer disabled:opacity-40"
      aria-label={label}
    />
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function ExportDialog({ onClose }: Props) {
  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [loadingTree, setLoadingTree] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<ExportCategory>>(new Set());

  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  // Overwrite confirmation state
  const [showOverwrite, setShowOverwrite] = useState(false);
  const pendingFileHandle = useRef<FileSystemFileHandle | null>(null);
  const pendingZipBlob = useRef<Blob | null>(null);

  // ── Load tree data ─────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadingTree(true);
      setLoadError(null);
      try {
        // Split into two Promise.all calls (TypeScript overloads only handle ≤10 items)
        const [sitesResp, classesResp, locsResp, productsResp, routesResp, dispsResp] =
          await Promise.all([
            fetchSites(),
            fetchEquipmentClasses(),
            fetchStorageLocations(),
            fetchProducts(),
            fetchAllRoutes(),
            fetchDispositions(),
          ]);
        const [matsResp, uomsResp, schedulesResp, defsResp, reasons] =
          await Promise.all([
            fetchMaterials(),
            fetchUoMs(),
            fetchWorkSchedules(),
            fetchDataDefinitions(),
            fetchReasons(),
          ]);

        if (cancelled) return;

        // For reason codes — only show top-level (no parent)
        const topReasons = reasons.filter((r) => r.parent_id === null);

        const cats: CategoryConfig[] = [
          {
            key: "sites",
            label: "Sites",
            items: sitesResp.data.map((s) => ({ id: s.id, label: s.code })),
          },
          {
            key: "equipment_classes",
            label: "Equipment Classes",
            items: classesResp.data.map((c) => ({ id: c.id, label: c.code })),
          },
          {
            key: "storage_locations",
            label: "Storage Locations",
            items: locsResp.data.map((l) => ({ id: l.id, label: l.code })),
          },
          {
            key: "products",
            label: "Products",
            items: productsResp.data.map((p) => ({
              id: p.id,
              label: p.code,
            })),
          },
          {
            key: "routes",
            label: "Routes",
            items: routesResp.data.map((r) => ({
              id: r.id,
              label: r.version ? `${r.name} v${r.version}` : r.name,
            })),
          },
          {
            key: "dispositions",
            label: "Dispositions",
            items: dispsResp.data.map((d) => ({ id: d.id, label: d.code })),
          },
          {
            key: "materials",
            label: "Materials",
            items: matsResp.data.map((m) => ({ id: m.id, label: m.code })),
          },
          {
            key: "uom",
            label: "Units of Measure",
            items: uomsResp.data.map((u) => ({ id: u.id, label: u.symbol })),
          },
          {
            key: "work_schedules",
            label: "Work Schedules",
            items: schedulesResp.data.map((s) => ({
              id: s.id,
              label: s.name,
            })),
          },
          {
            key: "data_definitions",
            label: "Data Definitions",
            items: defsResp.data.map((d) => ({ id: d.id, label: d.code })),
          },
          {
            key: "reason_codes",
            label: "Reason Codes",
            items: topReasons.map((r) => ({ id: r.id, label: r.code })),
          },
        ];

        setCategories(cats);
      } catch (err) {
        if (!cancelled) {
          setLoadError("Failed to load entity lists. Check server connection.");
        }
      } finally {
        if (!cancelled) setLoadingTree(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Selection helpers ──────────────────────────────────────────────

  const allKeys = categories.flatMap((cat) =>
    cat.items.map((item) => itemKey(cat.key, item.id)),
  );

  const allState: CheckState = getCheckState(allKeys, selected);

  const toggleAll = useCallback(() => {
    if (allState === "checked") {
      setSelected(new Set());
    } else {
      setSelected(new Set(allKeys));
    }
  }, [allState, allKeys]);

  const getCategoryKeys = (cat: CategoryConfig) =>
    cat.items.map((item) => itemKey(cat.key, item.id));

  const toggleCategory = useCallback(
    (cat: CategoryConfig) => {
      const keys = getCategoryKeys(cat);
      const state = getCheckState(keys, selected);
      setSelected((prev) => {
        const next = new Set(prev);
        if (state === "checked") {
          keys.forEach((k) => next.delete(k));
        } else {
          keys.forEach((k) => next.add(k));
        }
        return next;
      });
    },
    [selected],
  );

  const toggleItem = useCallback(
    (category: ExportCategory, id: string) => {
      const key = itemKey(category, id);
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return next;
      });
    },
    [],
  );

  const toggleExpanded = (catKey: ExportCategory) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(catKey)) next.delete(catKey);
      else next.add(catKey);
      return next;
    });
  };

  // ── Build ExportSelection from selected keys ───────────────────────

  function buildSelection(): ExportSelection {
    const sel: ExportSelection = {
      sites: [],
      equipment_classes: [],
      storage_locations: [],
      products: [],
      routes: [],
      dispositions: [],
      materials: [],
      uom: [],
      work_schedules: [],
      data_definitions: [],
      reason_codes: [],
    };
    for (const key of selected) {
      const colonIdx = key.indexOf(":");
      const cat = key.slice(0, colonIdx) as ExportCategory;
      const id = key.slice(colonIdx + 1);
      (sel[cat] as string[]).push(id);
    }
    return sel;
  }

  // ── Save zip to disk ──────────────────────────────────────────────

  const ZIP_FILENAME = "mes_export.zip";

  /**
   * Write a blob to a FileSystemFileHandle and update status on success.
   */
  async function writeZipToHandle(
    handle: FileSystemFileHandle,
    blob: Blob,
  ): Promise<void> {
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    setExportStatus(`Saved as "${handle.name}".`);
  }

  function triggerDownload(blob: Blob): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = ZIP_FILENAME;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setExportStatus("Download started.");
  }

  /**
   * Write blob to an already-acquired FileSystemFileHandle.
   * Performs an in-app overwrite confirmation when the target file already
   * has content. Call this AFTER obtaining the handle with showSaveFilePicker
   * so that the picker is invoked while the user gesture is still active.
   */
  async function saveToHandle(
    handle: FileSystemFileHandle,
    blob: Blob,
  ): Promise<void> {
    // Check whether the target file already has content so we can show
    // a custom in-app overwrite confirmation before writing.
    let existingSize = 0;
    try {
      const existing = await handle.getFile();
      existingSize = existing.size;
    } catch {
      // New file — proceed without confirmation.
    }

    if (existingSize > 0) {
      pendingFileHandle.current = handle;
      pendingZipBlob.current = blob;
      setShowOverwrite(true);
      return; // resumes in handleOverwriteConfirm / handleOverwriteCancel
    }

    await writeZipToHandle(handle, blob);
  }

  async function handleOverwriteConfirm() {
    const handle = pendingFileHandle.current;
    const blob = pendingZipBlob.current;
    pendingFileHandle.current = null;
    pendingZipBlob.current = null;
    setShowOverwrite(false);
    if (!handle || !blob) return;
    setExporting(true);
    try {
      await writeZipToHandle(handle, blob);
    } catch (err) {
      setExportError("Failed to write file: " + String(err));
    } finally {
      setExporting(false);
    }
  }

  function handleOverwriteCancel() {
    pendingFileHandle.current = null;
    pendingZipBlob.current = null;
    setShowOverwrite(false);
    setExportStatus(null);
  }

  // ── Export handler ─────────────────────────────────────────────────

  async function handleExport() {
    if (selected.size === 0) return;

    // Acquire the file handle FIRST, while the click gesture is still active.
    // showSaveFilePicker is blocked by browsers once the transient user
    // activation expires — which happens after long async chains like building
    // a large export (many API calls).  Getting the handle before building the
    // zip guarantees the picker always appears, regardless of export size.
    let handle: FileSystemFileHandle | null = null;
    if ("showSaveFilePicker" in window) {
      try {
        handle = await window.showSaveFilePicker({
          suggestedName: ZIP_FILENAME,
          startIn: "downloads",
          types: [
            {
              description: "ZIP Archive",
              accept: { "application/zip": [".zip"] },
            },
          ],
        });
      } catch {
        // User cancelled the picker — nothing to do.
        return;
      }
    }

    setExporting(true);
    setExportError(null);
    setExportStatus("Building export data…");
    try {
      const selection = buildSelection();
      const blob = await buildExportZip(selection, (msg) =>
        setExportStatus(msg),
      );
      if (handle) {
        await saveToHandle(handle, blob);
      } else {
        triggerDownload(blob);
      }
    } catch (err) {
      setExportError("Export failed: " + String(err));
      setExportStatus(null);
    } finally {
      setExporting(false);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  const isDone =
    exportStatus !== null &&
    (exportStatus.startsWith("Saved") || exportStatus.startsWith("Download"));

  return (
    <Dialog
      open
      onClose={() => {
        if (!exporting) onClose();
      }}
      className="relative z-50"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40" aria-hidden="true" />

      {/* Panel */}
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="relative w-full max-w-lg rounded-xl bg-white shadow-2xl flex flex-col max-h-[90vh]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 shrink-0">
            <div className="flex items-center gap-2">
              <ArrowDownTrayIcon className="h-5 w-5 text-indigo-600" />
              <DialogTitle className="text-base font-semibold text-gray-900">
                Export Design Time Objects
              </DialogTitle>
            </div>
            <button
              onClick={onClose}
              disabled={exporting && !isDone}
              className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-40"
              aria-label="Close"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {loadingTree ? (
              <div className="flex items-center justify-center py-12 text-sm text-gray-500">
                <svg
                  className="mr-2 h-4 w-4 animate-spin text-indigo-500"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"
                  />
                </svg>
                Loading entities…
              </div>
            ) : loadError ? (
              <p className="py-8 text-center text-sm text-red-600">
                {loadError}
              </p>
            ) : (
              <div className="space-y-0.5 text-sm select-none">
                {/* Root "All" node */}
                <div className="flex items-center gap-2 py-1 px-1 rounded hover:bg-gray-50">
                  <Checkbox
                    state={allState}
                    onChange={toggleAll}
                    label="Select all"
                  />
                  <span className="font-semibold text-gray-800">All</span>
                  <span className="text-xs text-gray-400">
                    ({selected.size} of {allKeys.length} selected)
                  </span>
                </div>

                {/* Category nodes */}
                {categories.map((cat) => {
                  const catKeys = getCategoryKeys(cat);
                  const catState = getCheckState(catKeys, selected);
                  const isExpanded = expanded.has(cat.key);

                  return (
                    <div key={cat.key}>
                      {/* Category row */}
                      <div className="flex items-center gap-1.5 py-1 px-1 rounded hover:bg-gray-50">
                        {/* Expand toggle */}
                        <button
                          onClick={() => toggleExpanded(cat.key)}
                          className="p-0.5 text-gray-400 hover:text-gray-700 transition-colors"
                          aria-label={
                            isExpanded ? "Collapse" : "Expand"
                          }
                          disabled={cat.items.length === 0}
                        >
                          {isExpanded ? (
                            <ChevronDownIcon className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronRightIcon className="h-3.5 w-3.5" />
                          )}
                        </button>
                        <Checkbox
                          state={catState}
                          onChange={() => toggleCategory(cat)}
                          label={`Select all ${cat.label}`}
                        />
                        <button
                          onClick={() => toggleExpanded(cat.key)}
                          className="flex-1 text-left font-medium text-gray-700 hover:text-gray-900"
                        >
                          {cat.label}
                        </button>
                        <span className="text-xs text-gray-400">
                          {cat.items.filter((item) =>
                            selected.has(itemKey(cat.key, item.id)),
                          ).length}{" "}
                          / {cat.items.length}
                        </span>
                      </div>

                      {/* Item rows */}
                      {isExpanded && (
                        <div className="ml-8 space-y-0.5">
                          {cat.items.length === 0 ? (
                            <p className="py-1 px-2 text-xs text-gray-400 italic">
                              No items
                            </p>
                          ) : (
                            cat.items.map((item) => {
                              const key = itemKey(cat.key, item.id);
                              const isChecked = selected.has(key);
                              return (
                                <label
                                  key={item.id}
                                  className="flex items-center gap-2 py-0.5 px-1 rounded hover:bg-gray-50 cursor-pointer"
                                >
                                  <input
                                    type="checkbox"
                                    checked={isChecked}
                                    onChange={() =>
                                      toggleItem(cat.key, item.id)
                                    }
                                    className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                  />
                                  <span className="text-gray-700 font-mono text-xs">
                                    {item.label}
                                  </span>
                                </label>
                              );
                            })
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Status bar */}
          {(exportStatus || exportError) && (
            <div
              className={`shrink-0 border-t px-6 py-2 text-xs ${
                exportError
                  ? "border-red-100 bg-red-50 text-red-700"
                  : isDone
                  ? "border-green-100 bg-green-50 text-green-700"
                  : "border-gray-100 bg-gray-50 text-gray-600"
              }`}
            >
              {exportError ? exportError : exportStatus}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4 shrink-0">
            <span className="text-xs text-gray-400">
              {selected.size === 0
                ? "Select items to export"
                : `${selected.size} item${selected.size !== 1 ? "s" : ""} selected`}
            </span>
            <div className="flex gap-3">
              <button
                onClick={onClose}
                disabled={exporting && !isDone}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-40"
              >
                {isDone ? "Close" : "Cancel"}
              </button>
              <button
                onClick={handleExport}
                disabled={
                  selected.size === 0 || loadingTree || exporting
                }
                className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {exporting && !isDone && (
                  <svg
                    className="h-4 w-4 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8z"
                    />
                  </svg>
                )}
                <ArrowDownTrayIcon className="h-4 w-4" />
                {exporting && !isDone ? "Exporting…" : "Export"}
              </button>
            </div>
          </div>
        </DialogPanel>
      </div>

      {/* Overwrite confirmation sub-dialog */}
      {showOverwrite && (
        <div
          className="fixed inset-0 z-10 flex items-center justify-center bg-black/20"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="w-80 rounded-lg bg-white shadow-xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-900">
              Overwrite existing file?
            </h3>
            <p className="text-sm text-gray-600">
              <span className="font-mono font-medium">{ZIP_FILENAME}</span>{" "}
              already exists at the selected location. Do you want to replace it?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={handleOverwriteCancel}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                No
              </button>
              <button
                onClick={handleOverwriteConfirm}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
              >
                Yes, overwrite
              </button>
            </div>
          </div>
        </div>
      )}
    </Dialog>
  );
}
