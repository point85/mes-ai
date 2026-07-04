/**
 * ImportDialog — select a MES AI export zip and import its objects into the DB.
 *
 * Phases:
 *   idle      → file not yet chosen
 *   reading   → parsing zip + running conflict detection
 *   conflicts → showing conflict list, user picks strategy
 *   asking    → asking about each conflict one-by-one (ask_each strategy)
 *   importing → running the import, progress shown
 *   done      → summary screen
 *   error     → fatal error before import could start
 */

import { useRef, useState, useCallback } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
  XMarkIcon,
  ArrowUpTrayIcon,
  DocumentArrowUpIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import {
  parseZip,
  detectConflicts,
  runImport,
  type ParsedZip,
  type ConflictItem,
  type ConflictResolution,
  type ImportResult,
} from "../utils/importUtils";

// ─── Types ───────────────────────────────────────────────────────────────────

type Phase = "idle" | "reading" | "conflicts" | "asking" | "importing" | "done" | "error";
type GlobalStrategy = "overwrite_all" | "skip_all" | "ask_each";

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  onClose: () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function conflictKey(category: string, importedId: string): string {
  return `${category}::${importedId}`;
}

function summarizeParsed(parsed: ParsedZip): string {
  const parts: string[] = [];
  if (parsed.uom.length)              parts.push(`${parsed.uom.length} UoM(s)`);
  if (parsed.equipment_classes.length) parts.push(`${parsed.equipment_classes.length} Equipment Class(es)`);
  if (parsed.storage_locations.length) parts.push(`${parsed.storage_locations.length} Storage Location(s)`);
  if (parsed.materials.length)        parts.push(`${parsed.materials.length} Material(s)`);
  if (parsed.dispositions.length)     parts.push(`${parsed.dispositions.length} Disposition(s)`);
  if (parsed.sites.length)            parts.push(`${parsed.sites.length} Site(s)`);
  if (parsed.products.length)         parts.push(`${parsed.products.length} Product(s)`);
  if (parsed.routes.length)           parts.push(`${parsed.routes.length} Route(s)`);
  if (parsed.work_schedules.length)   parts.push(`${parsed.work_schedules.length} Work Schedule(s)`);
  if (parsed.data_definitions.length) parts.push(`${parsed.data_definitions.length} Data Definition(s)`);
  if (parsed.reason_codes.length)     parts.push(`${parsed.reason_codes.length} Reason Code(s)`);
  return parts.length ? parts.join(", ") : "no recognisable objects";
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ImportDialog({ onClose }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [progressMsg, setProgressMsg] = useState<string>("");

  const [parsed, setParsed] = useState<ParsedZip | null>(null);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);

  // ask_each mode — queue of conflicts still to be answered
  const [askQueue, setAskQueue] = useState<ConflictItem[]>([]);
  const [resolutions, setResolutions] = useState<Map<string, ConflictResolution>>(new Map());

  const [result, setResult] = useState<ImportResult | null>(null);

  // ── Step 1: file chosen ────────────────────────────────────────────────────
  const handleFile = useCallback(async (file: File) => {
    setPhase("reading");
    setErrorMsg(null);
    setProgressMsg("Reading archive…");
    try {
      const p = await parseZip(file);
      setParsed(p);
      setProgressMsg("Checking for conflicts…");
      const c = await detectConflicts(p);
      setConflicts(c);
      setPhase("conflicts");
    } catch (e) {
      setErrorMsg(String(e));
      setPhase("error");
    }
  }, []);

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      // reset so same file can be re-picked
      e.target.value = "";
    },
    [handleFile],
  );

  // ── Step 2: strategy chosen ────────────────────────────────────────────────
  const startImportWithStrategy = useCallback(
    async (strategy: GlobalStrategy, resolvedMap: Map<string, ConflictResolution>) => {
      if (!parsed) return;

      // Build the full resolutions map
      const finalMap = new Map<string, ConflictResolution>();
      if (strategy === "overwrite_all") {
        for (const c of conflicts) finalMap.set(conflictKey(c.category, c.importedId), "overwrite");
      } else if (strategy === "skip_all") {
        for (const c of conflicts) finalMap.set(conflictKey(c.category, c.importedId), "skip");
      } else {
        // ask_each — use the already-collected map
        for (const [k, v] of resolvedMap) finalMap.set(k, v);
      }

      setPhase("importing");
      setProgressMsg("Starting import…");
      try {
        const r = await runImport(parsed, conflicts, finalMap, (msg) => setProgressMsg(msg));
        setResult(r);
        setPhase("done");
      } catch (e) {
        setErrorMsg(String(e));
        setPhase("error");
      }
    },
    [parsed, conflicts],
  );

  const handleOverwriteAll = () => startImportWithStrategy("overwrite_all", new Map());
  const handleSkipAll = () => startImportWithStrategy("skip_all", new Map());

  const handleAskEach = () => {
    setAskQueue([...conflicts]);
    setResolutions(new Map());
    setPhase("asking");
  };

  // ── Step 2b: ask-each individual response ─────────────────────────────────
  const answerConflict = useCallback(
    (resolution: ConflictResolution) => {
      const current = askQueue[0];
      if (!current) return;
      const newMap = new Map(resolutions);
      newMap.set(conflictKey(current.category, current.importedId), resolution);
      const remaining = askQueue.slice(1);
      setResolutions(newMap);
      setAskQueue(remaining);
      if (remaining.length === 0) {
        // All answered — start import
        startImportWithStrategy("ask_each", newMap);
      }
    },
    [askQueue, resolutions, startImportWithStrategy],
  );

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <Dialog open onClose={() => { if (phase !== "importing") onClose(); }} className="relative z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="relative w-full max-w-lg rounded-xl bg-white shadow-2xl flex flex-col max-h-[90vh]">

          {/* Header */}
          <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 shrink-0">
            <ArrowUpTrayIcon className="h-6 w-6 text-indigo-600 shrink-0" />
            <DialogTitle className="text-base font-semibold text-gray-900 flex-1">
              Import
            </DialogTitle>
            {phase !== "importing" && (
              <button
                onClick={onClose}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                aria-label="Close"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            )}
          </div>

          {/* Body */}
          <div className="overflow-y-auto flex-1 px-6 py-5">

            {/* ── idle ── */}
            {phase === "idle" && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Choose a MES AI export archive (<code className="font-mono text-xs bg-gray-100 px-1 rounded">.zip</code>)
                  to import into the current database. The archive must have been created by the{" "}
                  <strong>Export</strong> feature.
                </p>
                <p className="text-sm text-gray-500">
                  You will be asked how to handle any objects whose code or name already exists in the database
                  before any data is written.
                </p>
                <div className="pt-2">
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                  >
                    <DocumentArrowUpIcon className="h-4 w-4" />
                    Choose File…
                  </button>
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".zip,application/zip"
                  className="hidden"
                  onChange={onFileChange}
                />
              </div>
            )}

            {/* ── reading ── */}
            {phase === "reading" && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <svg className="h-5 w-5 animate-spin text-indigo-600" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <p className="text-sm text-gray-700">{progressMsg}</p>
                </div>
              </div>
            )}

            {/* ── conflicts ── */}
            {phase === "conflicts" && parsed && (
              <div className="space-y-4">
                <p className="text-sm text-gray-700">
                  Archive contains: <span className="font-medium">{summarizeParsed(parsed)}</span>.
                </p>

                {conflicts.length === 0 ? (
                  <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
                    No conflicts detected — all objects are new.
                  </p>
                ) : (
                  <>
                    <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
                      <strong>{conflicts.length}</strong> object{conflicts.length !== 1 ? "s" : ""} already
                      exist{conflicts.length === 1 ? "s" : ""} in the database:
                    </p>
                    <ul className="max-h-44 overflow-y-auto divide-y divide-gray-100 border border-gray-200 rounded-md text-sm">
                      {conflicts.map((c) => (
                        <li key={c.importedId} className="flex items-center gap-2 px-3 py-1.5 text-gray-700">
                          <ExclamationTriangleIcon className="h-4 w-4 text-amber-500 shrink-0" />
                          <span className="font-medium text-gray-500 min-w-[120px]">{c.category}</span>
                          <span className="truncate">{c.label}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                <div>
                  <p className="text-sm font-medium text-gray-800 mb-2">
                    {conflicts.length === 0
                      ? "Proceed with import?"
                      : "How should conflicts be handled?"}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={handleOverwriteAll}
                      className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                    >
                      {conflicts.length === 0 ? "Import" : "Overwrite All"}
                    </button>
                    {conflicts.length > 0 && (
                      <>
                        <button
                          onClick={handleSkipAll}
                          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          Skip All Conflicts
                        </button>
                        <button
                          onClick={handleAskEach}
                          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          Ask for Each
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ── asking (ask-each) ── */}
            {phase === "asking" && askQueue.length > 0 && (
              <div className="space-y-4">
                <p className="text-xs text-gray-500">
                  Conflict {conflicts.length - askQueue.length + 1} of {conflicts.length}
                </p>
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <div className="flex items-start gap-2">
                    <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {askQueue[0].category}: <span className="font-bold">{askQueue[0].label}</span>
                      </p>
                      <p className="text-sm text-gray-600 mt-0.5">
                        This {askQueue[0].category.toLowerCase()} already exists in the database.
                        Overwrite it with the imported version, or skip it?
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => answerConflict("overwrite")}
                    className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                  >
                    Overwrite
                  </button>
                  <button
                    onClick={() => answerConflict("skip")}
                    className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Skip
                  </button>
                </div>
              </div>
            )}

            {/* ── importing ── */}
            {phase === "importing" && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <svg className="h-5 w-5 animate-spin text-indigo-600 shrink-0" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <p className="text-sm font-medium text-gray-700">Importing — do not close this dialog</p>
                </div>
                <p className="text-xs text-gray-500 ml-8 truncate">{progressMsg}</p>
              </div>
            )}

            {/* ── done ── */}
            {phase === "done" && result && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 shrink-0" />
                  <p className="text-base font-semibold text-gray-900">Import complete</p>
                </div>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <dt className="text-gray-500">Created</dt>
                  <dd className="font-medium text-gray-900">{result.created}</dd>
                  <dt className="text-gray-500">Updated</dt>
                  <dd className="font-medium text-gray-900">{result.updated}</dd>
                  <dt className="text-gray-500">Skipped</dt>
                  <dd className="font-medium text-gray-900">{result.skipped}</dd>
                  <dt className="text-gray-500">Errors</dt>
                  <dd className={`font-medium ${result.errors.length > 0 ? "text-red-600" : "text-gray-900"}`}>
                    {result.errors.length}
                  </dd>
                </dl>

                {result.errors.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-red-700 mb-1">Error details:</p>
                    <ul className="max-h-36 overflow-y-auto text-xs text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 space-y-0.5">
                      {result.errors.map((e, i) => (
                        <li key={i} className="truncate">{e}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <p className="text-xs text-gray-500">
                  Refresh the relevant pages to see the imported data.
                </p>
              </div>
            )}

            {/* ── error ── */}
            {phase === "error" && (
              <div className="space-y-3">
                <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                  <ExclamationTriangleIcon className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800">Import failed</p>
                    <p className="text-sm text-red-700 mt-0.5 break-words">{errorMsg}</p>
                  </div>
                </div>
                <button
                  onClick={() => { setPhase("idle"); setErrorMsg(null); }}
                  className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors"
                >
                  ← Try again
                </button>
              </div>
            )}
          </div>

          {/* Footer */}
          {(phase === "done" || phase === "conflicts" || phase === "idle" || phase === "error") && (
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end shrink-0">
              {phase === "done" ? (
                <button
                  onClick={onClose}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                >
                  Close
                </button>
              ) : phase === "conflicts" ? (
                <button
                  onClick={onClose}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              ) : phase === "asking" ? null : (
                <button
                  onClick={onClose}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
