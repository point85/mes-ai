/**
 * Plugin Detail Page — shows full plugin info, parameters, config editor, and lifecycle controls.
 *
 * For plugins with typed parameters (e.g. AVEVA Historian), the config editor
 * renders proper GUI controls: dropdowns for equipment/auth_mode/state_model,
 * checkboxes for booleans, number inputs for integers, password inputs for secrets.
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeftIcon,
  PlayIcon,
  StopIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  PlusIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import {
  usePlugin,
  useInstallPlugin,
  useUninstallPlugin,
  useUpdatePluginConfig,
  useEnablePlugin,
  useDisablePlugin,
} from "../../hooks/usePlugins";
import { useAllEquipment } from "../../hooks/usePhysicalModel";
import { useStateModels } from "../../hooks/usePerformance";
import type { ParameterSchema } from "../../types";
import { formatApiError } from "../../api/errors";

/** Known enum values for select controls. */
const AUTH_MODE_OPTIONS = ["negotiate", "bearer", "basic"];

/** Resolve the current value for a parameter from config_values or parameter_values. */
function resolveValue(
  plugin: { parameter_values: Record<string, unknown>; config_values: Record<string, unknown> },
  param: ParameterSchema,
): unknown {
  // config_overrides win over install-time parameter_values
  if (param.name in plugin.config_values) return plugin.config_values[param.name];
  if (param.name in plugin.parameter_values) return plugin.parameter_values[param.name];
  return param.default ?? "";
}

export default function PluginDetailPage() {
  const { pluginId } = useParams<{ pluginId: string }>();
  const navigate = useNavigate();
  const { data: plugin, isLoading, error } = usePlugin(pluginId!);
  const installMut = useInstallPlugin();
  const uninstallMut = useUninstallPlugin();
  const updateConfigMut = useUpdatePluginConfig();
  const enableMut = useEnablePlugin();
  const disableMut = useDisablePlugin();

  // Reference data for dropdowns
  const { data: equipmentResp } = useAllEquipment();
  const { data: stateModels } = useStateModels();

  const equipmentList = equipmentResp?.data ?? [];
  const stateModelList = stateModels ?? [];

  // Parameter values (used for both install and post-install editing)
  const [paramValues, setParamValues] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);

  // Seed paramValues when plugin data loads or changes
  useEffect(() => {
    if (!plugin) return;
    if (plugin.installed) {
      // For installed plugins, seed from resolved values
      const resolved: Record<string, unknown> = {};
      for (const p of plugin.parameters) {
        resolved[p.name] = resolveValue(plugin, p);
      }
      setParamValues(resolved);
    } else {
      // For pre-install, seed from defaults only
      const defaults: Record<string, unknown> = {};
      for (const p of plugin.parameters) {
        if (p.default != null) defaults[p.name] = p.default;
      }
      setParamValues(defaults);
    }
    setDirty(false);
  }, [plugin]);

  function setParam(name: string, value: unknown) {
    setParamValues((prev) => ({ ...prev, [name]: value }));
    setDirty(true);
  }

  function handleSaveConfig() {
    if (!pluginId) return;
    updateConfigMut.mutate(
      { pluginId, config_overrides: paramValues },
      { onSuccess: () => setDirty(false) },
    );
  }

  function handleInstall() {
    if (!pluginId) return;
    // Convert all values to strings for the install endpoint
    const strValues: Record<string, string> = {};
    for (const [k, v] of Object.entries(paramValues)) {
      if (v != null && v !== "") strValues[k] = String(v);
    }
    installMut.mutate({ pluginId, parameter_values: strValues });
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500 p-6">Loading plugin…</p>;
  }
  if (error || !plugin) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Plugin not found or failed to load.
        </div>
      </div>
    );
  }

  const status = !plugin.installed
    ? "available"
    : plugin.error
      ? "error"
      : !plugin.enabled
        ? "disabled"
        : plugin.is_running
          ? "running"
          : "stopped";

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/plugins")}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{plugin.name}</h1>
          <p className="text-sm text-gray-500">
            {plugin.id} v{plugin.version}
            {plugin.author && <> &middot; {plugin.author}</>}
            {plugin.origin && (
              <>
                {" "}
                &middot;{" "}
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  plugin.origin === "system" ? "bg-purple-50 text-purple-700" : "bg-teal-50 text-teal-700"
                }`}>
                  {plugin.origin}
                </span>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Status + Lifecycle Controls */}
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            status === "running"
              ? "bg-green-50 text-green-700"
              : status === "error"
                ? "bg-red-50 text-red-700"
                : status === "disabled"
                  ? "bg-yellow-50 text-yellow-700"
                  : status === "available"
                    ? "bg-blue-50 text-blue-700"
                    : "bg-gray-100 text-gray-600"
          }`}
        >
          {status}
        </span>

        {!plugin.installed ? (
          plugin.parameters.length === 0 ? (
            <button
              onClick={handleInstall}
              disabled={installMut.isPending}
              className="inline-flex items-center gap-1 rounded-md border border-indigo-300 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50 transition-colors"
            >
              <ArrowDownTrayIcon className="h-3.5 w-3.5" /> Install
            </button>
          ) : null
        ) : (
          <>
            {plugin.enabled ? (
              <button
                onClick={() => disableMut.mutate(pluginId!)}
                disabled={disableMut.isPending}
                className="inline-flex items-center gap-1 rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-50 transition-colors"
              >
                <StopIcon className="h-3.5 w-3.5" /> Disable
              </button>
            ) : (
              <button
                onClick={() => enableMut.mutate(pluginId!)}
                disabled={enableMut.isPending}
                className="inline-flex items-center gap-1 rounded-md border border-green-300 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-50 transition-colors"
              >
                <PlayIcon className="h-3.5 w-3.5" /> Enable
              </button>
            )}
            <button
              onClick={() => uninstallMut.mutate(pluginId!)}
              disabled={uninstallMut.isPending}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-red-50 hover:text-red-700 transition-colors"
            >
              <TrashIcon className="h-3.5 w-3.5" /> Uninstall
            </button>
          </>
        )}
      </div>

      {plugin.error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          <strong>Error:</strong> {plugin.error}
        </div>
      )}

      {/* Mutation error banner — surfaces 422 "Required parameter missing",
          503 adapter-connect failures, etc. so enable/install failures are visible. */}
      {(() => {
        const muts: Array<[string, { error: unknown } | undefined]> = [
          ["Enable failed", enableMut.error ? { error: enableMut.error } : undefined],
          ["Disable failed", disableMut.error ? { error: disableMut.error } : undefined],
          ["Install failed", installMut.error ? { error: installMut.error } : undefined],
          ["Uninstall failed", uninstallMut.error ? { error: uninstallMut.error } : undefined],
          ["Save configuration failed", updateConfigMut.error ? { error: updateConfigMut.error } : undefined],
        ];
        const active = muts.find(([, v]) => v !== undefined);
        if (!active) return null;
        const [label, holder] = active;
        return (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            <strong>{label}:</strong>{" "}
            {formatApiError(holder!.error, "Request failed — see server log for details.")}
          </div>
        );
      })()}

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard label="Description" value={plugin.description || "—"} />
        {plugin.comment && <InfoCard label="Comment" value={plugin.comment} />}
        <InfoCard label="Category" value={plugin.category || "—"} />
        <InfoCard label="Min MES Version" value={plugin.min_mes_version} />
        <InfoCard
          label="Extension Points"
          value={plugin.extension_points.join(", ") || "—"}
        />
        <InfoCard
          label="Event Subscriptions"
          value={plugin.event_subscriptions.join(", ") || "—"}
        />
        <InfoCard
          label="Dependencies"
          value={plugin.dependencies.join(", ") || "—"}
        />
        <InfoCard
          label="Required Permissions"
          value={plugin.required_core_permissions.join(", ") || "—"}
        />
      </div>

      {/* Parameters section — typed form for both install and post-install editing */}
      {plugin.parameters.length > 0 && (
        <div className="rounded-lg border border-gray-200 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">
            {plugin.installed ? "Configuration" : "Plugin Parameters"}
          </h2>
          <div className="space-y-3">
            {plugin.parameters.map((param: ParameterSchema) =>
              param.type === "array" && param.items?.length ? (
                <ParameterArrayField
                  key={param.name}
                  param={param}
                  value={paramValues[param.name]}
                  onChange={(v) => setParam(param.name, v)}
                  equipmentList={equipmentList}
                  stateModelList={stateModelList}
                />
              ) : (
                <ParameterField
                  key={param.name}
                  param={param}
                  value={paramValues[param.name]}
                  onChange={(v) => setParam(param.name, v)}
                  equipmentList={equipmentList}
                  stateModelList={stateModelList}
                />
              ),
            )}
          </div>

          {!plugin.installed ? (
            <button
              onClick={handleInstall}
              disabled={installMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors disabled:opacity-50"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              {installMut.isPending ? "Installing…" : "Install"}
            </button>
          ) : (
            <button
              onClick={handleSaveConfig}
              disabled={updateConfigMut.isPending || !dirty}
              className="inline-flex items-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors disabled:opacity-50"
            >
              {updateConfigMut.isPending ? "Saving…" : "Save Configuration"}
            </button>
          )}
        </div>
      )}

      {/* Notes */}
      {plugin.notes && (
        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">Admin Notes</h2>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{plugin.notes}</p>
        </div>
      )}

      {/* Permissions */}
      {plugin.permissions.length > 0 && (
        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">
            Custom Permissions
          </h2>
          <ul className="text-sm text-gray-600 space-y-1">
            {plugin.permissions.map((perm) => (
              <li key={perm.id}>
                <code className="text-xs bg-gray-100 px-1 rounded">{perm.id}</code>
                {perm.description && (
                  <span className="text-gray-400 ml-2">— {perm.description}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
      <dt className="text-xs font-medium text-gray-400 uppercase tracking-wider">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-gray-700">{value}</dd>
    </div>
  );
}

// ─── Typed Parameter Field ───────────────────────────────────────────

interface EquipmentOption {
  id: string;
  name: string;
  code: string;
}

interface StateModelOption {
  model_id: string;
  name: string;
}

interface ParameterFieldProps {
  param: ParameterSchema;
  value: unknown;
  onChange: (value: unknown) => void;
  equipmentList: EquipmentOption[];
  stateModelList: StateModelOption[];
}

const INPUT_CLS =
  "flex-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500";
const SELECT_CLS =
  "flex-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500";

function ParameterField({
  param,
  value,
  onChange,
  equipmentList,
  stateModelList,
}: ParameterFieldProps) {
  const strVal = value != null ? String(value) : "";

  // Determine control type based on parameter name, type, and semantic hints
  const control = resolveControl(param);

  return (
    <div className="flex items-start gap-3">
      <div className="w-48 shrink-0">
        <label className="text-sm font-medium text-gray-700">
          {formatLabel(param.name)}
          {param.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <p className="text-xs text-gray-400 mt-0.5">{param.description}</p>
      </div>

      {control === "equipment_select" ? (
        <select
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
          className={SELECT_CLS}
        >
          <option value="">— Select equipment —</option>
          {equipmentList.map((eq) => (
            <option key={eq.id} value={eq.id}>
              {eq.name} ({eq.code})
            </option>
          ))}
        </select>
      ) : control === "auth_mode_select" ? (
        <select
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
          className={SELECT_CLS}
        >
          <option value="">— Select auth mode —</option>
          {AUTH_MODE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      ) : control === "state_model_select" ? (
        <select
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
          className={SELECT_CLS}
        >
          <option value="">— Select state model —</option>
          {stateModelList.map((sm) => (
            <option key={sm.model_id} value={sm.model_id}>
              {sm.name} ({sm.model_id})
            </option>
          ))}
        </select>
      ) : control === "boolean_checkbox" ? (
        <label className="flex items-center gap-2 py-1.5">
          <input
            type="checkbox"
            checked={value === true || value === "true"}
            onChange={(e) => onChange(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-gray-600">
            {value === true || value === "true" ? "Enabled" : "Disabled"}
          </span>
        </label>
      ) : control === "number_input" ? (
        <input
          type="number"
          value={strVal}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          placeholder={param.default != null ? String(param.default) : ""}
          className={INPUT_CLS}
        />
      ) : control === "password_input" ? (
        <input
          type="password"
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder="••••••"
          autoComplete="off"
          className={INPUT_CLS}
        />
      ) : (
        <input
          type="text"
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={param.default != null ? String(param.default) : ""}
          className={INPUT_CLS}
        />
      )}
    </div>
  );
}

// ─── Typed Array Parameter Field ─────────────────────────────────────

function ParameterArrayField({
  param,
  value,
  onChange,
  equipmentList,
  stateModelList,
}: ParameterFieldProps) {
  // Value is stored as a JSON string or an array
  const items: Record<string, unknown>[] = (() => {
    if (Array.isArray(value)) return value;
    if (typeof value === "string" && value) {
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed;
      } catch {
        /* not JSON */
      }
    }
    return [];
  })();

  const itemSchemas = param.items ?? [];

  function updateItem(index: number, field: string, fieldValue: unknown) {
    const next = items.map((item, i) =>
      i === index ? { ...item, [field]: fieldValue } : item,
    );
    onChange(JSON.stringify(next));
  }

  function addItem() {
    const blank: Record<string, unknown> = {};
    for (const s of itemSchemas) {
      blank[s.name] = s.default ?? "";
    }
    onChange(JSON.stringify([...items, blank]));
  }

  function removeItem(index: number) {
    onChange(JSON.stringify(items.filter((_, i) => i !== index)));
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700">
            {formatLabel(param.name)}
          </label>
          <p className="text-xs text-gray-400">{param.description}</p>
        </div>
        <button
          type="button"
          onClick={addItem}
          className="inline-flex items-center gap-1 rounded-md border border-indigo-300 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50 transition-colors"
        >
          <PlusIcon className="h-3.5 w-3.5" /> Add mapping
        </button>
      </div>

      {items.length === 0 && (
        <p className="text-xs text-gray-400 italic">No mappings configured yet.</p>
      )}

      {items.map((item, idx) => (
        <div
          key={idx}
          className="relative rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2"
        >
          <button
            type="button"
            onClick={() => removeItem(idx)}
            className="absolute top-2 right-2 rounded p-0.5 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
            title="Remove mapping"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>

          <span className="text-xs font-semibold text-gray-500 uppercase">
            Mapping {idx + 1}
          </span>

          {itemSchemas.map((itemParam) => (
            <ParameterField
              key={itemParam.name}
              param={itemParam}
              value={item[itemParam.name]}
              onChange={(v) => updateItem(idx, itemParam.name, v)}
              equipmentList={equipmentList}
              stateModelList={stateModelList}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

type ControlType =
  | "equipment_select"
  | "auth_mode_select"
  | "state_model_select"
  | "boolean_checkbox"
  | "number_input"
  | "password_input"
  | "text_input";

function resolveControl(param: ParameterSchema): ControlType {
  // Secret fields always get password input
  if (param.secret) return "password_input";

  // Semantic matching by parameter name
  if (param.name === "equipment_id") return "equipment_select";
  if (param.name === "auth_mode") return "auth_mode_select";
  if (param.name === "state_model_id") return "state_model_select";

  // Type-based matching
  if (param.type === "boolean") return "boolean_checkbox";
  if (param.type === "integer" || param.type === "number") return "number_input";

  return "text_input";
}

/** Convert snake_case parameter name to a readable label. */
function formatLabel(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bId\b/, "ID")
    .replace(/\bUrl\b/, "URL")
    .replace(/\bFqn\b/, "FQN")
    .replace(/\bSsl\b/, "SSL")
    .replace(/\bSec\b/, "(sec)");
}
