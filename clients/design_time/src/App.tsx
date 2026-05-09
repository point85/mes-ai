/**
 * DT-CLIENT entry point — sets up React Router + TanStack Query.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "./components/layout";
import { AuthProvider } from "./contexts/AuthContext";
import AuthGuard from "./components/AuthGuard";
import LoginPage from "./pages/login/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import { UoMListPage } from "./pages/uom";
import { SiteListPage } from "./pages/sites";
import { AreaListPage } from "./pages/areas";
import { LineListPage } from "./pages/lines";
import { WorkCellListPage } from "./pages/work-cells";
import { EquipmentListPage, EquipmentMaterialPage, EquipmentCapabilityPage } from "./pages/equipment";
import { EquipmentClassListPage, EquipmentClassDetailPage } from "./pages/equipment-classes";
import { ProductListPage, ProductDetailPage, BOMEditorPage } from "./pages/products";
import { RouteEditorPage } from "./pages/routes";
import { MaterialListPage, MaterialLotListPage } from "./pages/materials";
import { DataDefListPage } from "./pages/data-collection";
import { GenealogyViewerPage } from "./pages/genealogy";
import { DispatchPage } from "./pages/dispatch";
import { PluginListPage, PluginDetailPage } from "./pages/plugins";
import { ReasonListPage } from "./pages/reasons";
import { UserListPage } from "./pages/admin/users";
import { RoleListPage } from "./pages/admin/roles";
import { DispositionListPage } from "./pages/dispositions";
import { StorageLocationListPage } from "./pages/storage-locations";
import { WorkScheduleListPage, WorkScheduleDetailPage } from "./pages/work-schedules";
import SettingsPage from "./pages/SettingsPage";
import DemoCpgPage from "./pages/DemoCpgPage";
import DemoElectronicsPage from "./pages/DemoElectronicsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes (no auth required) */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes */}
            <Route element={<AuthGuard />}>
              <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/uom" element={<UoMListPage />} />
            {/* ISA-95 Plant Model hierarchy */}
            <Route path="/sites" element={<SiteListPage />} />
            <Route path="/sites/:siteId/areas" element={<AreaListPage />} />
            <Route path="/areas/:areaId/lines" element={<LineListPage />} />
            <Route path="/lines/:lineId/work-cells" element={<WorkCellListPage />} />
            <Route path="/work-cells/:wcId/equipment" element={<EquipmentListPage />} />
            <Route path="/equipment/:equipId/materials" element={<EquipmentMaterialPage />} />
            <Route path="/equipment/:equipId/capabilities" element={<EquipmentCapabilityPage />} />
            <Route path="/equipment-classes" element={<EquipmentClassListPage />} />
            <Route path="/equipment-classes/:classId" element={<EquipmentClassDetailPage />} />
            {/* Products & Materials */}
            <Route path="/products" element={<ProductListPage />} />
            <Route path="/products/:productId" element={<ProductDetailPage />} />
            <Route path="/products/:productId/boms" element={<BOMEditorPage />} />
            <Route path="/routes" element={<RouteEditorPage />} />
            <Route path="/materials" element={<MaterialListPage />} />
            <Route path="/material-lots" element={<MaterialLotListPage />} />
            <Route path="/data-definitions" element={<DataDefListPage />} />
            <Route path="/reasons" element={<ReasonListPage />} />
            <Route path="/dispositions" element={<DispositionListPage />} />
            <Route path="/genealogy" element={<GenealogyViewerPage />} />
            <Route path="/dispatch" element={<DispatchPage />} />
            <Route path="/storage-locations" element={<StorageLocationListPage />} />
            {/* Work Schedules */}
            <Route path="/work-schedules" element={<WorkScheduleListPage />} />
            <Route path="/work-schedules/:scheduleId" element={<WorkScheduleDetailPage />} />
            {/* Plugin Management */}
              <Route path="/plugins" element={<PluginListPage />} />
              <Route path="/plugins/:pluginId" element={<PluginDetailPage />} />
              {/* Admin */}
              <Route path="/admin/users" element={<UserListPage />} />
              <Route path="/admin/roles" element={<RoleListPage />} />
              <Route path="/admin/settings" element={<SettingsPage />} />
              {/* Demos */}
              <Route path="/demos/cpg" element={<DemoCpgPage />} />
              <Route path="/demos/electronics" element={<DemoElectronicsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
