/**
 * Axios instance configured for the MES API.
 * In dev, Vite proxies /api → http://localhost:8000.
 */

import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// TODO: Add JWT token interceptor when auth is wired up
// api.interceptors.request.use((config) => {
//   const token = localStorage.getItem("mes_token");
//   if (token) config.headers.Authorization = `Bearer ${token}`;
//   return config;
// });

export default api;
