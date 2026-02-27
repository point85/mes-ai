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
import { WorkCenterListPage } from "./pages/work-centers";
import { EquipmentListPage } from "./pages/equipment";
import { ProductListPage } from "./pages/products";
import { MaterialListPage } from "./pages/materials";
import { DataDefListPage } from "./pages/data-collection";
import { OrderListPage } from "./pages/orders";
import { QualityTestListPage, NCListPage } from "./pages/quality";
import { PerformancePage } from "./pages/performance";
import { GenealogyViewerPage } from "./pages/genealogy";
import { DispatchPage } from "./pages/dispatch";

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
            <Route path="/lines/:lineId/work-centers" element={<WorkCenterListPage />} />
            <Route path="/work-centers/:wcId/equipment" element={<EquipmentListPage />} />
            {/* Products & Materials */}
            <Route path="/products" element={<ProductListPage />} />
            <Route path="/materials" element={<MaterialListPage />} />
            <Route path="/data-definitions" element={<DataDefListPage />} />
            <Route path="/orders" element={<OrderListPage />} />
            <Route path="/quality-tests" element={<QualityTestListPage />} />
            <Route path="/non-conformances" element={<NCListPage />} />
            <Route path="/performance" element={<PerformancePage />} />
            <Route path="/genealogy" element={<GenealogyViewerPage />} />
            <Route path="/dispatch" element={<DispatchPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
