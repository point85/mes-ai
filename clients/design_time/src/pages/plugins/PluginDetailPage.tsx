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
const AUTH_TYPE_OPTIONS = ["oauth2", "basic", "api_key"];

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
          {pluginId === "modbus-equipment" ? (
            <ModbusParameterForm
              params={plugin.parameters}
              values={paramValues}
              onChange={setParam}
              equipmentList={equipmentList}
              stateModelList={stateModelList}
            />
          ) : (
          <div className="space-y-3">
            {plugin.parameters
              .filter((param: ParameterSchema) => {
                // Only show token_url when OAuth2 auth is selected
                if (param.name === "token_url") {
                  const authType = String(paramValues["auth_type"] ?? "oauth2");
                  return authType === "oauth2";
                }
                return true;
              })
              .map((param: ParameterSchema) =>
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
                  siblingValues={paramValues}
                />
              ),
            )}
          </div>
          )}

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
  /** Values for sibling parameters in the same form — used to derive dynamic
      labels/help (e.g. client_id label changes based on auth_type). */
  siblingValues?: Record<string, unknown>;
}

/**
 * Dynamic labels for credential fields that depend on the current auth_type.
 * Keyed as `<param_name>::<auth_type>` → [label, description].
 */
const CREDENTIAL_LABEL_OVERRIDES: Record<string, { label: string; description: string }> = {
  "client_id::oauth2": { label: "Client ID", description: "OAuth2 client ID" },
  "client_secret::oauth2": { label: "Client Secret", description: "OAuth2 client secret" },
  "client_id::basic": { label: "Username", description: "HTTP Basic auth username" },
  "client_secret::basic": { label: "Password", description: "HTTP Basic auth password" },
  "client_id::api_key": { label: "API Key Name", description: "API key identifier (often unused; leave blank if not required)" },
  "client_secret::api_key": { label: "API Key", description: "API key value sent in the auth header" },
};

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
  siblingValues,
}: ParameterFieldProps) {
  const strVal = value != null ? String(value) : "";

  // Determine control type based on parameter name, type, and semantic hints
  const control = resolveControl(param);

  // Dynamic label/description: when the field is a credential whose meaning
  // depends on auth_type, swap the label and help text.
  const authType = siblingValues ? String(siblingValues["auth_type"] ?? "") : "";
  const overrideKey = `${param.name}::${authType}`;
  const override = CREDENTIAL_LABEL_OVERRIDES[overrideKey];
  const displayLabel = override?.label ?? formatLabel(param.name);
  const displayDescription = override?.description ?? param.description;

  return (
    <div className="flex items-start gap-3">
      <div className="w-48 shrink-0">
        <label className="text-sm font-medium text-gray-700">
          {displayLabel}
          {param.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <p className="text-xs text-gray-400 mt-0.5">{displayDescription}</p>
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
      ) : control === "auth_type_select" ? (
        <select
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
          className={SELECT_CLS}
        >
          <option value="">— Select authorization type —</option>
          {AUTH_TYPE_OPTIONS.map((opt) => (
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
              siblingValues={item}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Modbus-specific Parameter Form ──────────────────────────────────

const MODBUS_TCP_PARAMS = new Set(["host", "port"]);
const MODBUS_RTU_PARAMS = new Set(["serial_port", "baudrate", "bytesize", "parity", "stopbits"]);
const PARITY_OPTIONS = [
  { value: "N", label: "N — None" },
  { value: "E", label: "E — Even" },
  { value: "O", label: "O — Odd" },
];

interface ModbusParameterFormProps {
  params: ParameterSchema[];
  values: Record<string, unknown>;
  onChange: (name: string, value: unknown) => void;
  equipmentList: { id: string; name: string; code: string }[];
  stateModelList: { model_id: string; name: string }[];
}

function ModbusParameterForm({
  params,
  values,
  onChange,
  equipmentList,
  stateModelList,
}: ModbusParameterFormProps) {
  const mode = (values["mode"] as string) || "tcp";
  const byParam = Object.fromEntries(params.map((p) => [p.name, p]));

  function renderField(name: string) {
    const param = byParam[name];
    if (!param) return null;
    return (
      <ParameterField
        key={name}
        param={param}
        value={values[name]}
        onChange={(v) => onChange(name, v)}
        equipmentList={equipmentList}
        stateModelList={stateModelList}
        siblingValues={values}
      />
    );
  }

  const sectionCls = "rounded-md border border-gray-100 bg-gray-50 p-3 space-y-3";
  const labelCls = "text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2";

  return (
    <div className="space-y-4">
      {/* Mode radio */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">
          Transport Mode <span className="text-red-500">*</span>
        </p>
        <div className="flex gap-6">
          {(["tcp", "rtu"] as const).map((m) => (
            <label key={m} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="modbus_mode"
                value={m}
                checked={mode === m}
                onChange={() => onChange("mode", m)}
                className="h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500"
              />
              <span className="text-sm font-medium text-gray-700">
                {m === "tcp" ? "Modbus TCP" : "Modbus RTU (Serial)"}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* TCP parameters */}
      {mode === "tcp" && (
        <div className={sectionCls}>
          <p className={labelCls}>TCP Connection</p>
          {renderField("host")}
          {renderField("port")}
        </div>
      )}

      {/* RTU parameters */}
      {mode === "rtu" && (
        <div className={sectionCls}>
          <p className={labelCls}>Serial Port</p>
          {renderField("serial_port")}
          {renderField("baudrate")}
          <div className="flex items-start gap-3">
            <div className="w-48 shrink-0">
              <label className="text-sm font-medium text-gray-700">Parity</label>
              <p className="text-xs text-gray-400 mt-0.5">{byParam["parity"]?.description}</p>
            </div>
            <select
              value={(values["parity"] as string) || "N"}
              onChange={(e) => onChange("parity", e.target.value)}
              className="flex-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              {PARITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          {renderField("bytesize")}
          {renderField("stopbits")}
        </div>
      )}

      {/* Common parameters */}
      <div className={sectionCls}>
        <p className={labelCls}>Common</p>
        {renderField("unit_id")}
        {renderField("timeout")}
        {renderField("retries")}
        {renderField("poll_interval_sec")}
      </div>

      {/* Tag map */}
      <div className={sectionCls}>
        <p className={labelCls}>Tag Map</p>
        {renderField("tag_map")}
      </div>

      {/* State tracking */}
      <div className={sectionCls}>
        <p className={labelCls}>State Tracking</p>
        {renderField("equipment_id")}
        {renderField("state_model_id")}
        {renderField("state_tag")}
        {renderField("state_value_map")}
      </div>
    </div>
  );
}

type ControlType =
  | "equipment_select"
  | "auth_mode_select"
  | "auth_type_select"
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
  if (param.name === "auth_type") return "auth_type_select";
  if (param.name === "state_model_id") return "state_model_select";

  // Type-based matching
  if (param.type === "boolean") return "boolean_checkbox";
  if (param.type === "integer" || param.type === "number") return "number_input";

  return "text_input";
}

/** Convert snake_case parameter name to a readable label. */
function formatLabel(name: string): string {
  // Explicit overrides for cases where title-casing doesn't produce the desired label.
  const OVERRIDES: Record<string, string> = {
    auth_type: "Authorization Type",
  };
  if (OVERRIDES[name]) return OVERRIDES[name];
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bId\b/, "ID")
    .replace(/\bUrl\b/, "URL")
    .replace(/\bFqn\b/, "FQN")
    .replace(/\bSsl\b/, "SSL")
    .replace(/\bSec\b/, "(sec)");
}
