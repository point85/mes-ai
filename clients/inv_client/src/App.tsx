import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { InventoryPage } from "./pages/InventoryPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/inventory" replace />} />
        <Route path="/inventory" element={<InventoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/inventory" replace />} />
    </Routes>
  );
}