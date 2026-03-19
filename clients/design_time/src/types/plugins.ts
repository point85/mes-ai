/**
 * Plugin Management: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Plugin ────────────────────────────────────────────────────────────

export interface PluginSummary {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  is_loaded: boolean;
  is_running: boolean;
  enabled: boolean;
  error: string | null;
  extension_points: string[];
}

export interface PluginDetail extends PluginSummary {
  min_mes_version: string;
  permissions: { id: string; description: string }[];
  required_core_permissions: string[];
  event_subscriptions: string[];
  dependencies: string[];
  config_schema: Record<string, unknown>;
  config_values: Record<string, unknown>;
  notes: string | null;
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
