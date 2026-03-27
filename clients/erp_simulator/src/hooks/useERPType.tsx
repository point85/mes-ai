import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getSimulatorOptions } from "../api/erp";

interface ERPContextValue {
  erpType: "sap" | "oracle" | string;
  erpLabel: string;
}

const ERPContext = createContext<ERPContextValue>({ erpType: "sap", erpLabel: "SAP" });

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

  useEffect(() => {
    getSimulatorOptions()
      .then((opts) => setErpType(opts.erp_type))
      .catch(() => {});
  }, []);

  return (
    <ERPContext.Provider value={{ erpType, erpLabel: labelFor(erpType) }}>
      {children}
    </ERPContext.Provider>
  );
}
