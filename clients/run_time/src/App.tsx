import { useState, useCallback } from "react";
import Layout, { type TabId } from "./components/Layout";
import { useWebSocket } from "./hooks/useWebSocket";
import type { MESEvent } from "./types";
import DashboardPage from "./pages/DashboardPage";
import ScanPage from "./pages/ScanPage";
import ActiveWipPage from "./pages/ActiveWipPage";
import OrdersPage from "./pages/OrdersPage";
import EventsPage from "./pages/EventsPage";
import InventoryPage from "./pages/InventoryPage";
import EquipmentStatusPage from "./pages/EquipmentStatusPage";

const WS_TOPICS = ["wip.*", "operations.request.*", "dispatch.*", "quality.*", "data.*", "equipment.state.*"];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [events, setEvents] = useState<MESEvent[]>([]);

  const handleEvent = useCallback((event: MESEvent) => {
    setEvents((prev) => [...prev.slice(-499), event]);
  }, []);

  const { connected } = useWebSocket(WS_TOPICS, handleEvent);

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab} wsConnected={connected}>
      <div className={activeTab === "dashboard"  ? undefined : "hidden"}><DashboardPage events={events} /></div>
      <div className={activeTab === "scan"        ? undefined : "hidden"}><ScanPage /></div>
      <div className={activeTab === "active-wip"  ? undefined : "hidden"}><ActiveWipPage /></div>
      <div className={activeTab === "orders"      ? undefined : "hidden"}><OrdersPage /></div>
      <div className={activeTab === "inventory"   ? undefined : "hidden"}><InventoryPage /></div>
      <div className={activeTab === "equipment"   ? undefined : "hidden"}><EquipmentStatusPage /></div>
      <div className={activeTab === "events"      ? undefined : "hidden"}><EventsPage events={events} onClear={() => setEvents([])} /></div>
    </Layout>
  );
}
