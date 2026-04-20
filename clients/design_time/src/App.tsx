/**
 * DT-CLIENT entry point — sets up React Router + TanStack Query.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "./components/layout";
import DashboardPage from "./pages/DashboardPage";
import { UoMListPage } from "./pages/uom";
import { SiteListPage } from "./pages/sites";
import { AreaListPage } from "./pages/areas";
import { LineListPage } from "./pages/lines";
import { WorkCellListPage } from "./pages/work-cells";
import { EquipmentListPage, EquipmentMaterialPage, EquipmentCapabilityPage } from "./pages/equipment";
import { EquipmentClassListPage, EquipmentClassDetailPage } from "./pages/equipment-classes";
import { ProductListPage, ProductDetailPage } from "./pages/products";
import { RouteEditorPage } from "./pages/routes";
import { MaterialListPage } from "./pages/materials";
import { DataDefListPage } from "./pages/data-collection";
import { QualityTestListPage, NCListPage } from "./pages/quality";
import { PerformancePage } from "./pages/performance";
import { GenealogyViewerPage } from "./pages/genealogy";
import { DispatchPage } from "./pages/dispatch";
import { PluginListPage, PluginDetailPage } from "./pages/plugins";
import { ReasonListPage } from "./pages/reasons";
import { DispositionListPage } from "./pages/dispositions";
import { StorageLocationListPage } from "./pages/storage-locations";
import { InventoryBalancesPage, InventoryTransactionsPage } from "./pages/inventory";

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
        <Routes>
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
            <Route path="/routes" element={<RouteEditorPage />} />
            <Route path="/materials" element={<MaterialListPage />} />
            <Route path="/data-definitions" element={<DataDefListPage />} />
            <Route path="/quality-tests" element={<QualityTestListPage />} />
            <Route path="/non-conformances" element={<NCListPage />} />
            <Route path="/performance" element={<PerformancePage />} />
            <Route path="/reasons" element={<ReasonListPage />} />
            <Route path="/dispositions" element={<DispositionListPage />} />
            <Route path="/genealogy" element={<GenealogyViewerPage />} />
            <Route path="/dispatch" element={<DispatchPage />} />
            <Route path="/storage-locations" element={<StorageLocationListPage />} />
            <Route path="/inventory/balances" element={<InventoryBalancesPage />} />
            <Route path="/inventory/transactions" element={<InventoryTransactionsPage />} />
            {/* Plugin Management */}
            <Route path="/plugins" element={<PluginListPage />} />
            <Route path="/plugins/:pluginId" element={<PluginDetailPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
