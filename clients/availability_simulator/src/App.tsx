import { useState } from "react";
import Layout, { type TabId } from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import EquipmentPage from "./pages/EquipmentPage";
import TransitionPage from "./pages/TransitionPage";
import HistoryPage from "./pages/HistoryPage";
import ModelsPage from "./pages/ModelsPage";

const pages: Record<TabId, React.FC> = {
  dashboard: DashboardPage,
  equipment: EquipmentPage,
  transition: TransitionPage,
  history: HistoryPage,
  models: ModelsPage,
};

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const Page = pages[activeTab];

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab}>
      <Page />
    </Layout>
  );
}
