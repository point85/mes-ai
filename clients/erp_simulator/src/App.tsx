import { useState } from "react";
import Layout, { type TabId } from "./components/Layout";
import { ERPProvider } from "./hooks/useERPType";
import DashboardPage from "./pages/DashboardPage";
import OrdersPage from "./pages/OrdersPage";
import MaterialsPage from "./pages/MaterialsPage";
import ProductsPage from "./pages/ProductsPage";
import CompletionPage from "./pages/CompletionPage";
import ConsumptionPage from "./pages/ConsumptionPage";
import ScrapPage from "./pages/ScrapPage";
import QualityPage from "./pages/QualityPage";
import ConfirmationsPage from "./pages/ConfirmationsPage";

const pages: Record<TabId, React.FC> = {
  dashboard: DashboardPage,
  orders: OrdersPage,
  materials: MaterialsPage,
  products: ProductsPage,
  completion: CompletionPage,
  consumption: ConsumptionPage,
  scrap: ScrapPage,
  quality: QualityPage,
  confirmations: ConfirmationsPage,
};

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const Page = pages[activeTab];

  return (
    <ERPProvider>
      <Layout activeTab={activeTab} onTabChange={setActiveTab}>
        <Page />
      </Layout>
    </ERPProvider>
  );
}
