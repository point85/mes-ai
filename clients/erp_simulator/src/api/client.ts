import axios from "axios";

const ERP_PLUGIN_ID = "sap-erp-simulator";

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
    "X-MES-ERP-PLUGIN": ERP_PLUGIN_ID,
  },
});

export default api;
