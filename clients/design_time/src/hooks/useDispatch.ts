/**
 * TanStack Query hooks for the Dispatching Engine.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  evaluateDispatch,
  executeDispatch,
  fetchDispatchStrategies,
  fetchDispatchQueue,
} from "../api/dispatch";
import type {
  DispatchEvaluateRequest,
  DispatchExecuteRequest,
} from "../types";

const KEYS = {
  strategies: ["dispatchStrategies"] as const,
  queue: (workCellId: string) =>
    ["dispatchQueue", workCellId] as const,
};

export function useDispatchStrategies() {
  return useQuery({
    queryKey: KEYS.strategies,
    queryFn: () => fetchDispatchStrategies(),
  });
}

export function useDispatchQueue(workCellId: string, enabled = true) {
  return useQuery({
    queryKey: KEYS.queue(workCellId),
    queryFn: () => fetchDispatchQueue(workCellId),
    enabled: !!workCellId && enabled,
    refetchInterval: 10_000, // Auto-refresh queue every 10s
  });
}

export function useEvaluateDispatch() {
  return useMutation({
    mutationFn: (body: DispatchEvaluateRequest) => evaluateDispatch(body),
  });
}

export function useExecuteDispatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DispatchExecuteRequest) => executeDispatch(body),
    onSuccess: () => {
      // Invalidate all queue queries after dispatching
      qc.invalidateQueries({ queryKey: ["dispatchQueue"] });
    },
  });
}
