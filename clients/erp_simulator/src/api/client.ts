import axios from "axios";

const ERP_PLUGIN_HEADER = "X-MES-ERP-PLUGIN";

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Set the ERP plugin id that subsequent requests should target.
 *
 * The id is discovered at startup via /erp/simulator/options, which resolves
 * against the simulator bucket on the server. This ensures the dashboard's
 * health checks and CRUD operations hit the running simulator plugin instead
 * of any real ERP adapter that may also be loaded.
 */
export function setErpPluginId(pluginId: string | null | undefined): void {
  if (pluginId) {
    api.defaults.headers.common[ERP_PLUGIN_HEADER] = pluginId;
  } else {
    delete api.defaults.headers.common[ERP_PLUGIN_HEADER];
  }
}

export default api;
