/**
 * TanStack Query hooks for Work Schedules.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchWorkSchedules, fetchWorkSchedule, createWorkSchedule, updateWorkSchedule, deleteWorkSchedule,
  fetchShifts, createShift, updateShift, deleteShift,
  addBreak, deleteBreak,
  fetchRotations, createRotation, updateRotation, deleteRotation,
  addRotationSegment, deleteRotationSegment,
  fetchTeams, createTeam, updateTeam, deleteTeam,
  addTeamMember, deleteTeamMember,
  addMemberException, deleteMemberException,
  fetchNonWorkingPeriods, createNonWorkingPeriod, updateNonWorkingPeriod, deleteNonWorkingPeriod,
  fetchShiftInstancesForDay, fetchShiftInstancesForRange, fetchWorkingTime,
} from "../api/workSchedule";
import type {
  WorkScheduleCreate, WorkScheduleUpdate,
  WorkShiftCreate, WorkShiftUpdate,
  ShiftBreakCreate,
  WorkRotationCreate, WorkRotationUpdate,
  RotationSegmentCreate,
  WorkTeamCreate, WorkTeamUpdate,
  TeamMemberCreate,
  TeamMemberExceptionCreate,
  NonWorkingPeriodCreate, NonWorkingPeriodUpdate,
} from "../types";

const KEYS = {
  all: ["work-schedules"] as const,
  list: () => [...KEYS.all, "list"] as const,
  detail: (id: string) => [...KEYS.all, "detail", id] as const,
  shifts: (scheduleId: string) => [...KEYS.all, scheduleId, "shifts"] as const,
  rotations: (scheduleId: string) => [...KEYS.all, scheduleId, "rotations"] as const,
  teams: (scheduleId: string) => [...KEYS.all, scheduleId, "teams"] as const,
  nwp: (scheduleId: string) => [...KEYS.all, scheduleId, "nwp"] as const,
  instances_day: (scheduleId: string, day: string) => [...KEYS.all, scheduleId, "instances", "day", day] as const,
  instances_range: (scheduleId: string, from: string, to: string) => [...KEYS.all, scheduleId, "instances", "range", from, to] as const,
  working_time: (scheduleId: string, from: string, to: string) => [...KEYS.all, scheduleId, "working_time", from, to] as const,
};

// ── Schedules ─────────────────────────────────────────────────────────────────

export function useWorkSchedules() {
  return useQuery({ queryKey: KEYS.list(), queryFn: fetchWorkSchedules });
}

export function useWorkSchedule(id: string) {
  return useQuery({ queryKey: KEYS.detail(id), queryFn: () => fetchWorkSchedule(id), enabled: !!id });
}

export function useCreateWorkSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkScheduleCreate) => createWorkSchedule(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateWorkSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkScheduleUpdate & { id: string }) => updateWorkSchedule(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteWorkSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteWorkSchedule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

// ── Shifts ────────────────────────────────────────────────────────────────────

export function useShifts(scheduleId: string) {
  return useQuery({ queryKey: KEYS.shifts(scheduleId), queryFn: () => fetchShifts(scheduleId), enabled: !!scheduleId });
}

export function useCreateShift(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkShiftCreate) => createShift(scheduleId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateShift(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkShiftUpdate & { id: string }) => updateShift(scheduleId, id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteShift(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (shiftId: string) => deleteShift(scheduleId, shiftId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useAddBreak(scheduleId: string, shiftId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ShiftBreakCreate) => addBreak(scheduleId, shiftId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteBreak(scheduleId: string, shiftId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (breakId: string) => deleteBreak(scheduleId, shiftId, breakId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

// ── Rotations ─────────────────────────────────────────────────────────────────

export function useRotations(scheduleId: string) {
  return useQuery({ queryKey: KEYS.rotations(scheduleId), queryFn: () => fetchRotations(scheduleId), enabled: !!scheduleId });
}

export function useCreateRotation(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkRotationCreate) => createRotation(scheduleId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateRotation(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkRotationUpdate & { id: string }) => updateRotation(scheduleId, id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteRotation(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rotationId: string) => deleteRotation(scheduleId, rotationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useAddRotationSegment(scheduleId: string, rotationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RotationSegmentCreate) => addRotationSegment(scheduleId, rotationId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteRotationSegment(scheduleId: string, rotationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (segmentId: string) => deleteRotationSegment(scheduleId, rotationId, segmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

// ── Teams ─────────────────────────────────────────────────────────────────────

export function useTeams(scheduleId: string) {
  return useQuery({ queryKey: KEYS.teams(scheduleId), queryFn: () => fetchTeams(scheduleId), enabled: !!scheduleId });
}

export function useCreateTeam(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkTeamCreate) => createTeam(scheduleId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateTeam(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkTeamUpdate & { id: string }) => updateTeam(scheduleId, id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteTeam(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (teamId: string) => deleteTeam(scheduleId, teamId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useAddTeamMember(scheduleId: string, teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TeamMemberCreate) => addTeamMember(scheduleId, teamId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteTeamMember(scheduleId: string, teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memberPk: string) => deleteTeamMember(scheduleId, teamId, memberPk),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useAddMemberException(scheduleId: string, teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TeamMemberExceptionCreate) => addMemberException(scheduleId, teamId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteMemberException(scheduleId: string, teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (exceptionId: string) => deleteMemberException(scheduleId, teamId, exceptionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

// ── Non-Working Periods ───────────────────────────────────────────────────────

export function useNonWorkingPeriods(scheduleId: string) {
  return useQuery({ queryKey: KEYS.nwp(scheduleId), queryFn: () => fetchNonWorkingPeriods(scheduleId), enabled: !!scheduleId });
}

export function useCreateNonWorkingPeriod(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NonWorkingPeriodCreate) => createNonWorkingPeriod(scheduleId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateNonWorkingPeriod(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: NonWorkingPeriodUpdate & { id: string }) => updateNonWorkingPeriod(scheduleId, id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteNonWorkingPeriod(scheduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (periodId: string) => deleteNonWorkingPeriod(scheduleId, periodId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

// ── Query endpoints ──────────────────────────────────────────────────────────

export function useShiftInstancesForDay(scheduleId: string, day: string) {
  return useQuery({
    queryKey: KEYS.instances_day(scheduleId, day),
    queryFn: () => fetchShiftInstancesForDay(scheduleId, day),
    enabled: !!scheduleId && !!day,
  });
}

export function useShiftInstancesForRange(scheduleId: string, from_date: string, to_date: string) {
  return useQuery({
    queryKey: KEYS.instances_range(scheduleId, from_date, to_date),
    queryFn: () => fetchShiftInstancesForRange(scheduleId, from_date, to_date),
    enabled: !!scheduleId && !!from_date && !!to_date,
  });
}

export function useWorkingTime(scheduleId: string, from_dt: string, to_dt: string) {
  return useQuery({
    queryKey: KEYS.working_time(scheduleId, from_dt, to_dt),
    queryFn: () => fetchWorkingTime(scheduleId, from_dt, to_dt),
    enabled: !!scheduleId && !!from_dt && !!to_dt,
  });
}
