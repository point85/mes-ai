/**
 * Plugin Management API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  PluginSummary,
  PluginDetail,
  PluginInstallRequest,
  PluginConfigUpdate,
  AdapterInfo,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Plugins ──────────────────────────────────────────────────────────

export async function fetchPlugins(): Promise<ApiListResponse<PluginSummary>> {
  const { data } = await api.get<ApiListResponse<PluginSummary>>("/plugins");
  return data;
}

export async function fetchPlugin(pluginId: string): Promise<PluginDetail> {
  const { data } = await api.get<ApiResponse<PluginDetail>>(
    `/plugins/${encodeURIComponent(pluginId)}`,
  );
  return data.data;
}

export async function installPlugin(
  pluginId: string,
  body: PluginInstallRequest,
): Promise<Record<string, unknown>> {
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/install`,
    body,
  );
  return data.data;
}

export async function uninstallPlugin(
  pluginId: string,
): Promise<Record<string, unknown>> {
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/uninstall`,
  );
  return data.data;
}

export async function enablePlugin(pluginId: string): Promise<Record<string, unknown>> {
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/enable`,
  );
  return data.data;
}

export async function disablePlugin(pluginId: string): Promise<Record<string, unknown>> {
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/disable`,
  );
  return data.data;
}

export async function updatePluginConfig(
  pluginId: string,
  body: PluginConfigUpdate,
): Promise<Record<string, unknown>> {
  const { data } = await api.put<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/config`,
    body,
  );
  return data.data;
}

// ─── Adapter Catalog ──────────────────────────────────────────────────

export async function fetchAdapterCatalog(): Promise<ApiListResponse<AdapterInfo>> {
  const { data } = await api.get<ApiListResponse<AdapterInfo>>("/plugins/catalog");
  return data;
}
// ─── Kafka Java Bridge: build status + prepare ─────────────────────────────

export interface KafkaBridgeStatus {
  jar_exists: boolean;
  jar_path: string;
  stubs_exist: boolean;
  mvn_path: string | null;
}

export interface KafkaPrepareResult {
  jar_path: string;
  jar_existed: boolean;
  jar_built: boolean;
  stubs_existed: boolean;
  stubs_generated: boolean;
}

export async function fetchKafkaBridgeStatus(): Promise<KafkaBridgeStatus> {
  const { data } = await api.get<ApiResponse<KafkaBridgeStatus>>("/plugins/kafka-java-bridge/status");
  return data.data;
}

export async function prepareKafkaBridge(force = false): Promise<KafkaPrepareResult> {
  const { data } = await api.post<ApiResponse<KafkaPrepareResult>>(
    `/plugins/kafka-java-bridge/prepare?force=${force}`,
  );
  return data.data;
}

export interface KafkaTestResult {
  topic: string;
  sent: string;
  received: string;
  match: boolean;
}

export async function kafkaTestConnection(): Promise<KafkaTestResult> {
  const { data } = await api.post<ApiResponse<KafkaTestResult>>(
    "/plugins/kafka-java-bridge/test",
  );
  return data.data;
}