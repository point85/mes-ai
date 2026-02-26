/**
 * Dispatching Engine API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  DispatchEvaluateRequest,
  DispatchEvaluateResponse,
  DispatchExecuteRequest,
  DispatchExecuteResponse,
  DispatchStrategyInfo,
  DispatchQueueItem,
  ApiResponse,
} from "../types";

export async function evaluateDispatch(
  body: DispatchEvaluateRequest,
): Promise<DispatchEvaluateResponse> {
  const { data } = await api.post<ApiResponse<DispatchEvaluateResponse>>(
    "/dispatch/evaluate",
    body,
  );
  return data.data;
}

export async function executeDispatch(
  body: DispatchExecuteRequest,
): Promise<DispatchExecuteResponse> {
  const { data } = await api.post<ApiResponse<DispatchExecuteResponse>>(
    "/dispatch/execute",
    body,
  );
  return data.data;
}

export async function fetchDispatchStrategies(): Promise<DispatchStrategyInfo[]> {
  const { data } = await api.get<ApiResponse<DispatchStrategyInfo[]>>(
    "/dispatch/strategies",
  );
  return data.data;
}

export async function fetchDispatchQueue(
  workCenterId: string,
): Promise<DispatchQueueItem[]> {
  const { data } = await api.get<ApiResponse<DispatchQueueItem[]>>(
    `/dispatch/queue/${workCenterId}`,
  );
  return data.data;
}
