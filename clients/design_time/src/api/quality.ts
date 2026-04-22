/**
 * Quality Management API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  QualityTest,
  QualityTestCreate,
  QualityTestUpdate,
  TestResult,
  RecordResultRequest,
  NonConformance,
  NonConformanceCreate,
  NonConformanceUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Quality Tests ────────────────────────────────────────────────────

export async function fetchQualityTests(
  testType?: string,
): Promise<ApiListResponse<QualityTest>> {
  const params: Record<string, string> = { limit: "200" };
  if (testType) params.test_type = testType;
  const { data } = await api.get<ApiListResponse<QualityTest>>("/quality/tests", {
    params,
  });
  return data;
}

export async function fetchQualityTest(id: string): Promise<QualityTest> {
  const { data } = await api.get<ApiResponse<QualityTest>>(
    `/quality/tests/${id}`,
  );
  return data.data;
}

export async function createQualityTest(
  body: QualityTestCreate,
): Promise<QualityTest> {
  const { data } = await api.post<ApiResponse<QualityTest>>(
    "/quality/tests",
    body,
  );
  return data.data;
}

export async function updateQualityTest(
  id: string,
  body: QualityTestUpdate,
): Promise<QualityTest> {
  const { data } = await api.put<ApiResponse<QualityTest>>(
    `/quality/tests/${id}`,
    body,
  );
  return data.data;
}

export async function deleteQualityTest(id: string): Promise<void> {
  await api.delete(`/quality/tests/${id}`);
}

// ─── Test Results ─────────────────────────────────────────────────────

export async function fetchTestResults(
  testId?: string,
  result?: string,
): Promise<ApiListResponse<TestResult>> {
  const params: Record<string, string> = { limit: "200" };
  if (testId) params.test_id = testId;
  if (result) params.result = result;
  const { data } = await api.get<ApiListResponse<TestResult>>(
    "/quality/results",
    { params },
  );
  return data;
}

export async function recordTestResult(
  body: RecordResultRequest,
): Promise<TestResult> {
  const { data } = await api.post<ApiResponse<TestResult>>(
    "/quality/results",
    body,
  );
  return data.data;
}

// ─── Non-Conformances ─────────────────────────────────────────────────

export async function fetchNonConformances(
  status?: string,
  ncType?: string,
): Promise<ApiListResponse<NonConformance>> {
  const params: Record<string, string> = { limit: "200" };
  if (status) params.status = status;
  if (ncType) params.nc_type = ncType;
  const { data } = await api.get<ApiListResponse<NonConformance>>(
    "/quality/non-conformances",
    { params },
  );
  return data;
}

export async function createNonConformance(
  body: NonConformanceCreate,
): Promise<NonConformance> {
  const { data } = await api.post<ApiResponse<NonConformance>>(
    "/quality/non-conformances",
    body,
  );
  return data.data;
}

export async function updateNonConformance(
  id: string,
  body: NonConformanceUpdate,
): Promise<NonConformance> {
  const { data } = await api.put<ApiResponse<NonConformance>>(
    `/quality/non-conformances/${id}`,
    body,
  );
  return data.data;
}

export async function deleteNonConformance(id: string): Promise<void> {
  await api.delete(`/quality/non-conformances/${id}`);
}
