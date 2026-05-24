import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getSimulatorOptions, getERPHealth, type ERPHealth } from "../api/erp";

interface ERPContextValue {
  erpType: "sap" | "oracle" | string;
  erpLabel: string;
  /** Adapter health fetched automatically on mount. Null while loading or if server unreachable. */
  health: ERPHealth | null;
}

const ERPContext = createContext<ERPContextValue>({ erpType: "sap", erpLabel: "SAP", health: null });

export function useERPType() {
  return useContext(ERPContext);
}

function labelFor(t: string): string {
  switch (t) {
    case "sap": return "SAP";
    case "oracle": return "Oracle";
    default: return t.toUpperCase();
  }
}

export function ERPProvider({ children }: { children: ReactNode }) {
  const [erpType, setErpType] = useState<string>("sap");
  const [health, setHealth] = useState<ERPHealth | null>(null);

  useEffect(() => {
    // Resolve the simulator plugin id first so the health check targets it.
    getSimulatorOptions()
      .then((opts) => {
        setErpType(opts.erp_type);
        return getERPHealth();
      })
      .then((h) => { if (h) setHealth(h); })
      .catch(() => {});
  }, []);

  return (
    <ERPContext.Provider value={{ erpType, erpLabel: labelFor(erpType), health }}>
      {children}
    </ERPContext.Provider>
  );
}
