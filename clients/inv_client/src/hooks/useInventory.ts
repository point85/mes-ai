import { useState, useCallback, useMemo } from "react";
import {
  fetchInventoryTransactions,
  fetchInventoryBalances,
  fetchStorageLocations,
  fetchMaterialLots,
  receiveInventory,
  putawayInventory,
  pickInventory,
  transferInventory,
  consumeInventory,
  adjustInventory,
} from "../api";
import type {
  InventoryTransaction,
  InventoryBalance,
  StorageLocation,
  MaterialLot,
  ReceivePayload,
  PutawayPayload,
  PickPayload,
  TransferPayload,
  ConsumePayload,
  AdjustPayload,
  TrackingMethod,
} from "../types";

export function useInventory() {
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const locationMap = useMemo(() => new Map(locations.map((l) => [l.id, l])), [locations]);
  const lotMap = useMemo(() => new Map(lots.map((l) => [l.id, l])), [lots]);

  const loadRefData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [locs, mLots] = await Promise.all([fetchStorageLocations(), fetchMaterialLots()]);
      setLocations(locs);
      setLots(mLots);
    } catch (e) {
      setError("Failed to load reference data");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBalances = useCallback(async (filters?: {
    material_lot_id?: string;
    location_id?: string;
    tracking_method?: TrackingMethod;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInventoryBalances({ limit: 200, ...filters });
      setBalances(data);
    } catch (e) {
      setError("Failed to load balances");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTransactions = useCallback(async (filters?: {
    material_lot_id?: string;
    location_id?: string;
    transaction_type?: "receive" | "putaway" | "pick" | "move" | "transfer" | "consume" | "adjust";
    tracking_method?: TrackingMethod;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInventoryTransactions({ limit: 200, ...filters });
      setTransactions(data);
    } catch (e) {
      setError("Failed to load transactions");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const executeOperation = useCallback(async (operation: string, payload: any) => {
    setLoading(true);
    setError(null);
    try {
      let result;
      switch (operation) {
        case "receive":
          result = await receiveInventory(payload as ReceivePayload);
          break;
        case "putaway":
          result = await putawayInventory(payload as PutawayPayload);
          break;
        case "pick":
          result = await pickInventory(payload as PickPayload);
          break;
        case "transfer":
          result = await transferInventory(payload as TransferPayload);
          break;
        case "consume":
          result = await consumeInventory(payload as ConsumePayload);
          break;
        case "adjust":
          result = await adjustInventory(payload as AdjustPayload);
          break;
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
      return result;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Operation failed";
      setError(errorMsg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    // State
    locations,
    lots,
    balances,
    transactions,
    loading,
    error,
    locationMap,
    lotMap,
    // Actions
    loadRefData,
    loadBalances,
    loadTransactions,
    executeOperation,
    setError,
  };
}