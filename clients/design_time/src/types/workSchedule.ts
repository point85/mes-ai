/**
 * Work Schedule: TypeScript types mirroring server Pydantic schemas.
 */

export interface WorkScheduleSummary {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  shift_count: number;
  team_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkScheduleRead {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  shifts: WorkShiftRead[];
  rotations: WorkRotationRead[];
  teams: WorkTeamRead[];
  non_working_periods: NonWorkingPeriodRead[];
  created_at: string;
  updated_at: string;
}

export interface WorkScheduleCreate {
  name: string;
  description?: string | null;
}

export interface WorkScheduleUpdate {
  name?: string;
  description?: string | null;
}

// ── Shift ─────────────────────────────────────────────────────────────────────

export interface WorkShiftRead {
  id: string;
  work_schedule_id: string;
  name: string;
  description: string | null;
  start_time: string; // "HH:MM:SS"
  duration_seconds: number;
  is_active: boolean;
  breaks: ShiftBreakRead[];
  created_at: string;
  updated_at: string;
}

export interface WorkShiftCreate {
  name: string;
  description?: string | null;
  start_time: string;
  duration_seconds: number;
}

export interface WorkShiftUpdate {
  name?: string;
  description?: string | null;
  start_time?: string;
  duration_seconds?: number;
}

// ── Shift Break ───────────────────────────────────────────────────────────────

export interface ShiftBreakRead {
  id: string;
  shift_id: string;
  name: string;
  description: string | null;
  start_time: string;
  duration_seconds: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ShiftBreakCreate {
  name: string;
  description?: string | null;
  start_time: string;
  duration_seconds: number;
}

// ── Rotation ─────────────────────────────────────────────────────────────────

export interface RotationSegmentRead {
  id: string;
  rotation_id: string;
  shift_id: string;
  shift_name: string;
  days_on: number;
  days_off: number;
  sequence: number;
  is_active: boolean;
}

export interface RotationSegmentCreate {
  shift_id: string;
  days_on: number;
  days_off: number;
  sequence: number;
}

export interface WorkRotationRead {
  id: string;
  work_schedule_id: string;
  name: string;
  description: string | null;
  day_count: number;
  working_seconds: number;
  is_active: boolean;
  segments: RotationSegmentRead[];
  created_at: string;
  updated_at: string;
}

export interface WorkRotationCreate {
  name: string;
  description?: string | null;
  segments?: RotationSegmentCreate[];
}

export interface WorkRotationUpdate {
  name?: string;
  description?: string | null;
}

// ── Team ──────────────────────────────────────────────────────────────────────

export interface TeamMemberRead {
  id: string;
  team_id: string;
  member_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface TeamMemberCreate {
  member_id: string;
  name: string;
  description?: string | null;
}

export interface TeamMemberExceptionRead {
  id: string;
  team_id: string;
  shift_start: string;
  add_member_id: string | null;
  remove_member_id: string | null;
  reason: string | null;
  is_active: boolean;
}

export interface TeamMemberExceptionCreate {
  shift_start: string;
  add_member_id?: string | null;
  remove_member_id?: string | null;
  reason?: string | null;
}

export interface WorkTeamRead {
  id: string;
  work_schedule_id: string;
  name: string;
  description: string | null;
  rotation_id: string;
  rotation_start: string; // "YYYY-MM-DD"
  is_active: boolean;
  members: TeamMemberRead[];
  member_exceptions: TeamMemberExceptionRead[];
  created_at: string;
  updated_at: string;
}

export interface WorkTeamCreate {
  name: string;
  description?: string | null;
  rotation_id: string;
  rotation_start: string;
}

export interface WorkTeamUpdate {
  name?: string;
  description?: string | null;
  rotation_id?: string;
  rotation_start?: string;
}

// ── Non-Working Period ────────────────────────────────────────────────────────

export interface NonWorkingPeriodRead {
  id: string;
  work_schedule_id: string;
  name: string;
  description: string | null;
  start_datetime: string;
  duration_seconds: number;
  end_datetime: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NonWorkingPeriodCreate {
  name: string;
  description?: string | null;
  start_datetime: string;
  duration_seconds: number;
}

export interface NonWorkingPeriodUpdate {
  name?: string;
  description?: string | null;
  start_datetime?: string;
  duration_seconds?: number;
}

// ── Query results ─────────────────────────────────────────────────────────────

export interface ShiftInstanceResult {
  date: string;
  team_id: string;
  team_name: string;
  shift_id: string;
  shift_name: string;
  start_datetime: string;
  end_datetime: string;
}
