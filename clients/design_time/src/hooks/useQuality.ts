/**
 * TanStack Query hooks for Quality Management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchQualityTests,
  createQualityTest,
  updateQualityTest,
  deleteQualityTest,
  fetchTestResults,
  recordTestResult,
  fetchNonConformances,
  createNonConformance,
  updateNonConformance,
  deleteNonConformance,
} from "../api/quality";
import type {
  QualityTestCreate,
  QualityTestUpdate,
  RecordResultRequest,
  NonConformanceCreate,
  NonConformanceUpdate,
} from "../types";

const KEYS = {
  tests: ["qualityTests"] as const,
  testList: (type?: string) => ["qualityTests", "list", type] as const,
  results: ["testResults"] as const,
  resultList: (testId?: string, result?: string) =>
    ["testResults", "list", testId, result] as const,
  ncs: ["nonConformances"] as const,
  ncList: (status?: string, ncType?: string) =>
    ["nonConformances", "list", status, ncType] as const,
};

// ─── Quality Tests ────────────────────────────────────────────────────

export function useQualityTests(testType?: string) {
  return useQuery({
    queryKey: KEYS.testList(testType),
    queryFn: () => fetchQualityTests(testType),
  });
}

export function useCreateQualityTest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: QualityTestCreate) => createQualityTest(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.tests }),
  });
}

export function useUpdateQualityTest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: QualityTestUpdate & { id: string }) =>
      updateQualityTest(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.tests }),
  });
}

export function useDeleteQualityTest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteQualityTest(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.tests }),
  });
}

// ─── Test Results ─────────────────────────────────────────────────────

export function useTestResults(testId?: string, result?: string) {
  return useQuery({
    queryKey: KEYS.resultList(testId, result),
    queryFn: () => fetchTestResults(testId, result),
  });
}

export function useRecordTestResult() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecordResultRequest) => recordTestResult(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.results }),
  });
}

// ─── Non-Conformances ─────────────────────────────────────────────────

export function useNonConformances(status?: string, ncType?: string) {
  return useQuery({
    queryKey: KEYS.ncList(status, ncType),
    queryFn: () => fetchNonConformances(status, ncType),
  });
}

export function useCreateNonConformance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NonConformanceCreate) => createNonConformance(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.ncs }),
  });
}

export function useUpdateNonConformance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: NonConformanceUpdate & { id: string }) =>
      updateNonConformance(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.ncs }),
  });
}

export function useDeleteNonConformance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteNonConformance(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.ncs }),
  });
}
