import { useState, useCallback, useMemo } from "react";
import Layout, { type TabId } from "./components/Layout";
import { useWebSocket } from "./hooks/useWebSocket";
import type { MESEvent } from "./types";
import DashboardPage from "./pages/DashboardPage";
import ScanPage from "./pages/ScanPage";
import ActiveWipPage from "./pages/ActiveWipPage";
import OrdersPage from "./pages/OrdersPage";
import EventsPage from "./pages/EventsPage";

const WS_TOPICS = ["wip.*", "production.order.*", "dispatch.*", "quality.*", "data.*", "equipment.state.*"];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [events, setEvents] = useState<MESEvent[]>([]);

  const handleEvent = useCallback((event: MESEvent) => {
    setEvents((prev) => [...prev.slice(-499), event]);
  }, []);

  const { connected } = useWebSocket(WS_TOPICS, handleEvent);

  const page = useMemo(() => {
    switch (activeTab) {
      case "dashboard": return <DashboardPage events={events} />;
      case "scan": return <ScanPage />;
      case "active-wip": return <ActiveWipPage />;
      case "orders": return <OrdersPage />;
      case "events": return <EventsPage events={events} />;
    }
  }, [activeTab, events]);

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab} wsConnected={connected}>
      {page}
    </Layout>
  );
}
