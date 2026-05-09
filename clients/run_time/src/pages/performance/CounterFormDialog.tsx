import { useState } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { createOrUpdateCounter } from "../../api/runtime";
import type { CounterCreateUpdate } from "../../types";

interface Props {
  onClose: () => void;
  onSaved: () => void;
}

export default function CounterFormDialog({ onClose, onSaved }: Props) {
  const [form, setForm] = useState({
    equipment_id: "",
    order_id: "",
    shift_date: new Date().toISOString().slice(0, 10),
    good_count: "0",
    reject_count: "0",
    rework_count: "0",
    ideal_cycle_time_sec: "",
    actual_run_time_sec: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.equipment_id.trim() || !form.shift_date) {
      setError("Equipment ID and Shift Date are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const body: CounterCreateUpdate = {
        equipment_id: form.equipment_id.trim(),
        shift_date: form.shift_date,
        good_count: parseInt(form.good_count, 10) || 0,
        reject_count: parseInt(form.reject_count, 10) || 0,
        rework_count: parseInt(form.rework_count, 10) || 0,
        ...(form.order_id.trim() && { order_id: form.order_id.trim() }),
        ...(form.ideal_cycle_time_sec && { ideal_cycle_time_sec: parseFloat(form.ideal_cycle_time_sec) }),
        ...(form.actual_run_time_sec && { actual_run_time_sec: parseFloat(form.actual_run_time_sec) }),
      };
      await createOrUpdateCounter(body);
      onSaved();
      onClose();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "An error occurred";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const field = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500";

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              Record Production Counter
            </DialogTitle>
            <button onClick={onClose} className="rounded p-1 text-gray-400 hover:text-gray-600">
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Equipment ID *</label>
              <input value={form.equipment_id} onChange={(e) => set("equipment_id", e.target.value)}
                className={`${field} font-mono`} placeholder="UUID" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Order ID</label>
              <input value={form.order_id} onChange={(e) => set("order_id", e.target.value)} className={field} />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Shift Date *</label>
              <input type="date" value={form.shift_date}
                onChange={(e) => set("shift_date", e.target.value)} className={field} />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Good</label>
                <input type="number" min={0} value={form.good_count}
                  onChange={(e) => set("good_count", e.target.value)} className={field} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Reject</label>
                <input type="number" min={0} value={form.reject_count}
                  onChange={(e) => set("reject_count", e.target.value)} className={field} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Rework</label>
                <input type="number" min={0} value={form.rework_count}
                  onChange={(e) => set("rework_count", e.target.value)} className={field} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Ideal Cycle (s)</label>
                <input type="number" step="0.01" value={form.ideal_cycle_time_sec}
                  onChange={(e) => set("ideal_cycle_time_sec", e.target.value)} className={field} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Actual Run (s)</label>
                <input type="number" step="0.01" value={form.actual_run_time_sec}
                  onChange={(e) => set("actual_run_time_sec", e.target.value)} className={field} />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button type="submit" disabled={submitting}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50">
                {submitting ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
