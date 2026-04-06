import type { RouteStep } from "../types";

interface Props {
  steps: RouteStep[];
  currentStepId: string | null;
}

export default function RouteProgressBar({ steps, currentStepId }: Props) {
  const sorted = [...steps].sort((a, b) => a.sequence - b.sequence);
  const currentIdx = sorted.findIndex((s) => s.id === currentStepId);

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h4 className="font-semibold text-gray-700 mb-3">Route Progress</h4>
      <div className="flex items-center gap-1 overflow-x-auto">
        {sorted.map((step, i) => {
          let state: "done" | "current" | "upcoming";
          if (currentIdx < 0) {
            // No current step — all done or not started
            state = "upcoming";
          } else if (i < currentIdx) {
            state = "done";
          } else if (i === currentIdx) {
            state = "current";
          } else {
            state = "upcoming";
          }

          return (
            <div key={step.id} className="flex items-center">
              {i > 0 && (
                <div
                  className={`w-8 h-0.5 ${state === "done" || state === "current" ? "bg-indigo-400" : "bg-gray-200"}`}
                />
              )}
              <div
                className={`flex flex-col items-center min-w-[60px] ${
                  state === "current" ? "scale-110" : ""
                }`}
                title={step.name}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    state === "done"
                      ? "bg-indigo-600 text-white"
                      : state === "current"
                        ? "bg-indigo-500 text-white ring-2 ring-indigo-300"
                        : "bg-gray-200 text-gray-500"
                  }`}
                >
                  {step.sequence}
                </div>
                <span
                  className={`text-[10px] mt-1 text-center leading-tight max-w-[70px] truncate ${
                    state === "current" ? "text-indigo-700 font-semibold" : "text-gray-400"
                  }`}
                >
                  {step.name}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
