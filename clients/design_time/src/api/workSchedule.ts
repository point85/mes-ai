/**
 * Work Schedule API functions.
 */

import api from "./client";
import type {
  ApiListResponse,
  ApiResponse,
  WorkScheduleSummary,
  WorkScheduleRead,
  WorkScheduleCreate,
  WorkScheduleUpdate,
  WorkShiftRead,
  WorkShiftCreate,
  WorkShiftUpdate,
  ShiftBreakRead,
  ShiftBreakCreate,
  WorkRotationRead,
  WorkRotationCreate,
  WorkRotationUpdate,
  RotationSegmentRead,
  RotationSegmentCreate,
  WorkTeamRead,
  WorkTeamCreate,
  WorkTeamUpdate,
  TeamMemberRead,
  TeamMemberCreate,
  TeamMemberExceptionRead,
  TeamMemberExceptionCreate,
  NonWorkingPeriodRead,
  NonWorkingPeriodCreate,
  NonWorkingPeriodUpdate,
  ShiftInstanceResult,
} from "../types";

const BASE = "/work-schedules";

// ── WorkSchedule ─────────────────────────────────────────────────────────────

export async function fetchWorkSchedules(): Promise<ApiListResponse<WorkScheduleSummary>> {
  const { data } = await api.get<ApiListResponse<WorkScheduleSummary>>(BASE);
  return data;
}

export async function fetchWorkSchedule(id: string): Promise<WorkScheduleRead> {
  const { data } = await api.get<ApiResponse<WorkScheduleRead>>(`${BASE}/${id}`);
  return data.data;
}

export async function createWorkSchedule(body: WorkScheduleCreate): Promise<WorkScheduleRead> {
  const { data } = await api.post<ApiResponse<WorkScheduleRead>>(BASE, body);
  return data.data;
}

export async function updateWorkSchedule(id: string, body: WorkScheduleUpdate): Promise<WorkScheduleRead> {
  const { data } = await api.patch<ApiResponse<WorkScheduleRead>>(`${BASE}/${id}`, body);
  return data.data;
}

export async function deleteWorkSchedule(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`);
}

// ── Shifts ───────────────────────────────────────────────────────────────────

export async function fetchShifts(scheduleId: string): Promise<ApiListResponse<WorkShiftRead>> {
  const { data } = await api.get<ApiListResponse<WorkShiftRead>>(`${BASE}/${scheduleId}/shifts`);
  return data;
}

export async function createShift(scheduleId: string, body: WorkShiftCreate): Promise<WorkShiftRead> {
  const { data } = await api.post<ApiResponse<WorkShiftRead>>(`${BASE}/${scheduleId}/shifts`, body);
  return data.data;
}

export async function updateShift(scheduleId: string, shiftId: string, body: WorkShiftUpdate): Promise<WorkShiftRead> {
  const { data } = await api.patch<ApiResponse<WorkShiftRead>>(`${BASE}/${scheduleId}/shifts/${shiftId}`, body);
  return data.data;
}

export async function deleteShift(scheduleId: string, shiftId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/shifts/${shiftId}`);
}

// ── Breaks ───────────────────────────────────────────────────────────────────

export async function addBreak(scheduleId: string, shiftId: string, body: ShiftBreakCreate): Promise<ShiftBreakRead> {
  const { data } = await api.post<ApiResponse<ShiftBreakRead>>(`${BASE}/${scheduleId}/shifts/${shiftId}/breaks`, body);
  return data.data;
}

export async function deleteBreak(scheduleId: string, shiftId: string, breakId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/shifts/${shiftId}/breaks/${breakId}`);
}

// ── Rotations ────────────────────────────────────────────────────────────────

export async function fetchRotations(scheduleId: string): Promise<ApiListResponse<WorkRotationRead>> {
  const { data } = await api.get<ApiListResponse<WorkRotationRead>>(`${BASE}/${scheduleId}/rotations`);
  return data;
}

export async function createRotation(scheduleId: string, body: WorkRotationCreate): Promise<WorkRotationRead> {
  const { data } = await api.post<ApiResponse<WorkRotationRead>>(`${BASE}/${scheduleId}/rotations`, body);
  return data.data;
}

export async function updateRotation(scheduleId: string, rotationId: string, body: WorkRotationUpdate): Promise<WorkRotationRead> {
  const { data } = await api.patch<ApiResponse<WorkRotationRead>>(`${BASE}/${scheduleId}/rotations/${rotationId}`, body);
  return data.data;
}

export async function deleteRotation(scheduleId: string, rotationId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/rotations/${rotationId}`);
}

export async function addRotationSegment(scheduleId: string, rotationId: string, body: RotationSegmentCreate): Promise<RotationSegmentRead> {
  const { data } = await api.post<ApiResponse<RotationSegmentRead>>(`${BASE}/${scheduleId}/rotations/${rotationId}/segments`, body);
  return data.data;
}

export async function deleteRotationSegment(scheduleId: string, rotationId: string, segmentId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/rotations/${rotationId}/segments/${segmentId}`);
}

// ── Teams ────────────────────────────────────────────────────────────────────

export async function fetchTeams(scheduleId: string): Promise<ApiListResponse<WorkTeamRead>> {
  const { data } = await api.get<ApiListResponse<WorkTeamRead>>(`${BASE}/${scheduleId}/teams`);
  return data;
}

export async function createTeam(scheduleId: string, body: WorkTeamCreate): Promise<WorkTeamRead> {
  const { data } = await api.post<ApiResponse<WorkTeamRead>>(`${BASE}/${scheduleId}/teams`, body);
  return data.data;
}

export async function updateTeam(scheduleId: string, teamId: string, body: WorkTeamUpdate): Promise<WorkTeamRead> {
  const { data } = await api.patch<ApiResponse<WorkTeamRead>>(`${BASE}/${scheduleId}/teams/${teamId}`, body);
  return data.data;
}

export async function deleteTeam(scheduleId: string, teamId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/teams/${teamId}`);
}

export async function addTeamMember(scheduleId: string, teamId: string, body: TeamMemberCreate): Promise<TeamMemberRead> {
  const { data } = await api.post<ApiResponse<TeamMemberRead>>(`${BASE}/${scheduleId}/teams/${teamId}/members`, body);
  return data.data;
}

export async function deleteTeamMember(scheduleId: string, teamId: string, memberPk: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/teams/${teamId}/members/${memberPk}`);
}

export async function addMemberException(scheduleId: string, teamId: string, body: TeamMemberExceptionCreate): Promise<TeamMemberExceptionRead> {
  const { data } = await api.post<ApiResponse<TeamMemberExceptionRead>>(`${BASE}/${scheduleId}/teams/${teamId}/exceptions`, body);
  return data.data;
}

export async function deleteMemberException(scheduleId: string, teamId: string, exceptionId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/teams/${teamId}/exceptions/${exceptionId}`);
}

// ── Non-Working Periods ──────────────────────────────────────────────────────

export async function fetchNonWorkingPeriods(scheduleId: string): Promise<ApiListResponse<NonWorkingPeriodRead>> {
  const { data } = await api.get<ApiListResponse<NonWorkingPeriodRead>>(`${BASE}/${scheduleId}/non-working-periods`);
  return data;
}

export async function createNonWorkingPeriod(scheduleId: string, body: NonWorkingPeriodCreate): Promise<NonWorkingPeriodRead> {
  const { data } = await api.post<ApiResponse<NonWorkingPeriodRead>>(`${BASE}/${scheduleId}/non-working-periods`, body);
  return data.data;
}

export async function updateNonWorkingPeriod(scheduleId: string, periodId: string, body: NonWorkingPeriodUpdate): Promise<NonWorkingPeriodRead> {
  const { data } = await api.patch<ApiResponse<NonWorkingPeriodRead>>(`${BASE}/${scheduleId}/non-working-periods/${periodId}`, body);
  return data.data;
}

export async function deleteNonWorkingPeriod(scheduleId: string, periodId: string): Promise<void> {
  await api.delete(`${BASE}/${scheduleId}/non-working-periods/${periodId}`);
}

// ── Query endpoints ───────────────────────────────────────────────────────────

export async function fetchShiftInstancesForDay(scheduleId: string, day: string): Promise<ApiListResponse<ShiftInstanceResult>> {
  const { data } = await api.get<ApiListResponse<ShiftInstanceResult>>(`${BASE}/${scheduleId}/shift-instances/day`, {
    params: { day },
  });
  return data;
}

export async function fetchShiftInstancesForRange(scheduleId: string, from_date: string, to_date: string): Promise<ApiListResponse<ShiftInstanceResult>> {
  const { data } = await api.get<ApiListResponse<ShiftInstanceResult>>(`${BASE}/${scheduleId}/shift-instances/range`, {
    params: { from_date, to_date },
  });
  return data;
}

export async function fetchWorkingTime(scheduleId: string, from_dt: string, to_dt: string): Promise<{ working_seconds: number }> {
  const { data } = await api.get<ApiResponse<{ working_seconds: number }>>(`${BASE}/${scheduleId}/working-time`, {
    params: { from_dt, to_dt },
  });
  return data.data;
}
