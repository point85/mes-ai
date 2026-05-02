/**
 * Work Schedule Detail Page — tabbed editor for a single schedule.
 * Tabs: Shifts | Rotations | Teams | Non-Working Periods
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeftIcon, ChartBarIcon } from "@heroicons/react/24/outline";
import { useWorkSchedule } from "../../hooks/useWorkSchedule";
import ShiftsTab from "./tabs/ShiftsTab";
import RotationsTab from "./tabs/RotationsTab";
import TeamsTab from "./tabs/TeamsTab";
import NonWorkingPeriodsTab from "./tabs/NonWorkingPeriodsTab";
import ShiftInstancesDialog from "./ShiftInstancesDialog";

type Tab = "shifts" | "rotations" | "teams" | "non-working";

const TABS: { id: Tab; label: string }[] = [
  { id: "shifts", label: "Shifts" },
  { id: "rotations", label: "Rotations" },
  { id: "teams", label: "Teams" },
  { id: "non-working", label: "Non-Working Periods" },
];

export default function WorkScheduleDetailPage() {
  const { scheduleId } = useParams<{ scheduleId: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("shifts");
  const [showInstances, setShowInstances] = useState(false);

  const { data: schedule, isLoading, error } = useWorkSchedule(scheduleId ?? "");

  if (isLoading) return <p className="text-sm text-gray-500 p-6">Loading…</p>;
  if (error || !schedule) {
    return (
      <div className="p-6 text-sm text-red-700 bg-red-50 rounded-md">
        Failed to load work schedule.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <button
          onClick={() => navigate("/work-schedules")}
          className="mt-1 p-1 text-gray-400 hover:text-gray-700 transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{schedule.name}</h1>
          {schedule.description && (
            <p className="text-sm text-gray-500 mt-0.5">{schedule.description}</p>
          )}
        </div>
        <button
          onClick={() => setShowInstances(true)}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          title="Shift instances"
        >
          <ChartBarIcon className="h-4 w-4" /> Shift Instances
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={[
                "pb-2 text-sm font-medium border-b-2 transition-colors",
                tab === t.id
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700",
              ].join(" ")}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {tab === "shifts" && <ShiftsTab scheduleId={schedule.id} shifts={schedule.shifts} />}
      {tab === "rotations" && <RotationsTab scheduleId={schedule.id} rotations={schedule.rotations} shifts={schedule.shifts} />}
      {tab === "teams" && <TeamsTab scheduleId={schedule.id} teams={schedule.teams} rotations={schedule.rotations} />}
      {tab === "non-working" && <NonWorkingPeriodsTab scheduleId={schedule.id} periods={schedule.non_working_periods} />}

      {showInstances && (
        <ShiftInstancesDialog
          scheduleId={schedule.id}
          scheduleName={schedule.name}
          onClose={() => setShowInstances(false)}
        />
      )}
    </div>
  );
}
