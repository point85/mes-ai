import { createContext, useContext, useState, useCallback } from "react";
import Layout, { type TabId } from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import EquipmentPage from "./pages/EquipmentPage";
import HistoryPage from "./pages/HistoryPage";
import OEEPage from "./pages/OEEPage";
import SimulatorPage from "./pages/SimulatorPage";
import ModelsPage from "./pages/ModelsPage";

/** Shared equipment selection context so pages can link to each other. */
interface EquipmentContextValue {
  equipmentId: string | null;
  equipmentCode: string | null;
  setEquipment: (id: string | null, code: string | null) => void;
  navigateTo: (tab: TabId) => void;
}

const EquipmentContext = createContext<EquipmentContextValue>({
  equipmentId: null,
  equipmentCode: null,
  setEquipment: () => {},
  navigateTo: () => {},
});

export function useEquipmentContext() {
  return useContext(EquipmentContext);
}

const pages: Record<TabId, React.FC> = {
  dashboard: DashboardPage,
  equipment: EquipmentPage,
  history: HistoryPage,
  oee: OEEPage,
  simulator: SimulatorPage,
  models: ModelsPage,
};

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [equipmentId, setEquipmentId] = useState<string | null>(null);
  const [equipmentCode, setEquipmentCode] = useState<string | null>(null);

  const setEquipment = useCallback((id: string | null, code: string | null) => {
    setEquipmentId(id);
    setEquipmentCode(code);
  }, []);

  const navigateTo = useCallback((tab: TabId) => {
    setActiveTab(tab);
  }, []);

  const Page = pages[activeTab];

  return (
    <EquipmentContext.Provider value={{ equipmentId, equipmentCode, setEquipment, navigateTo }}>
      <Layout activeTab={activeTab} onTabChange={setActiveTab}>
        <Page />
      </Layout>
    </EquipmentContext.Provider>
  );
}
