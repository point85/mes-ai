/**
 * Plugin Management: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Parameter schema (declared by plugin author) ──────────────────────

export interface ParameterSchema {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default: unknown;
  secret: boolean;
}

// ─── Plugin summary (list view) ────────────────────────────────────────

export interface PluginSummary {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  comment: string;
  category: string;
  origin: string;
  installed: boolean;
  enabled: boolean;
  is_loaded: boolean;
  is_running: boolean;
  error: string | null;
  extension_points: string[];
}

// ─── Plugin detail ─────────────────────────────────────────────────────

export interface PluginDetail extends PluginSummary {
  min_mes_version: string;
  parameters: ParameterSchema[];
  parameter_values: Record<string, unknown>;
  permissions: { id: string; description: string }[];
  required_core_permissions: string[];
  event_subscriptions: string[];
  dependencies: string[];
  config_schema: Record<string, unknown>;
  config_values: Record<string, unknown>;
  notes: string | null;
}

// ─── Request bodies ────────────────────────────────────────────────────

export interface PluginInstallRequest {
  parameter_values: Record<string, unknown>;
  notes?: string | null;
}

export interface PluginConfigUpdate {
  config_overrides: Record<string, unknown>;
  notes?: string | null;
}

// ─── Adapter catalog ──────────────────────────────────────────────────

export interface AdapterInfo {
  type: string;
  category: string;
  description: string;
  install_extra: string | null;
  is_installed: boolean;
}
