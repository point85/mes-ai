import { createContext, useContext, useState, useCallback } from "react";
import Layout, { type TabId } from "./components/Layout";
import EquipmentTree from "./components/EquipmentTree";
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
  equipmentName: string | null;
  setEquipment: (id: string | null, code: string | null, name?: string | null) => void;
  navigateTo: (tab: TabId) => void;
}

const EquipmentContext = createContext<EquipmentContextValue>({
  equipmentId: null,
  equipmentCode: null,
  equipmentName: null,
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

const operationsTabs: TabId[] = ["equipment", "history", "oee"];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [equipmentId, setEquipmentId] = useState<string | null>(null);
  const [equipmentCode, setEquipmentCode] = useState<string | null>(null);
  const [equipmentName, setEquipmentName] = useState<string | null>(null);

  const setEquipment = useCallback((id: string | null, code: string | null, name?: string | null) => {
    setEquipmentId(id);
    setEquipmentCode(code);
    setEquipmentName(name ?? null);
  }, []);

  const navigateTo = useCallback((tab: TabId) => {
    setActiveTab(tab);
  }, []);

  const Page = pages[activeTab];

  const treePanel = operationsTabs.includes(activeTab) ? (
    <EquipmentTree
      selectedEquipmentId={equipmentId}
      onSelectEquipment={(id, code, name) => setEquipment(id, code, name)}
    />
  ) : undefined;

  return (
    <EquipmentContext.Provider value={{ equipmentId, equipmentCode, equipmentName, setEquipment, navigateTo }}>
      <Layout activeTab={activeTab} onTabChange={setActiveTab} treePanel={treePanel}>
        <Page />
      </Layout>
    </EquipmentContext.Provider>
  );
}
