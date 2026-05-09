import { useState } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { recordStateChange } from "../../api/runtime";
import type { StateChangeRequest } from "../../types";

const DISPATCH_CATS = [
  "available",
  "busy",
  "unavailable_planned",
  "unavailable_unplanned",
] as const;

const OEE_BUCKETS = [
  "uptime_value_add",
  "uptime_non_value",
  "downtime_planned",
  "downtime_unplanned",
  "excluded",
] as const;

interface Props {
  onClose: () => void;
  onSaved: () => void;
}

export default function StateChangeFormDialog({ onClose, onSaved }: Props) {
  const [form, setForm] = useState<{
    equipment_id: string;
    state_model: string;
    state: string;
    sub_state: string;
    dispatch_category: (typeof DISPATCH_CATS)[number];
    oee_bucket: (typeof OEE_BUCKETS)[number];
    started_at: string;
    reason_code: string;
    notes: string;
  }>({
    equipment_id: "",
    state_model: "default",
    state: "",
    sub_state: "",
    dispatch_category: "available",
    oee_bucket: "uptime_value_add",
    started_at: new Date().toISOString().slice(0, 16),
    reason_code: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.equipment_id.trim() || !form.state.trim()) {
      setError("Equipment ID and State are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const body: StateChangeRequest = {
        equipment_id: form.equipment_id.trim(),
        state_model: form.state_model || "default",
        state: form.state.trim(),
        dispatch_category: form.dispatch_category,
        oee_bucket: form.oee_bucket,
        started_at: new Date(form.started_at).toISOString(),
        ...(form.sub_state && { sub_state: form.sub_state }),
        ...(form.reason_code && { reason_code: form.reason_code }),
        ...(form.notes && { notes: form.notes }),
      };
      await recordStateChange(body);
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

  const field = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500";

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              Record State Change
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
                className={`${field} font-mono`} placeholder="UUID of the equipment" />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">State Model</label>
                <input value={form.state_model} onChange={(e) => set("state_model", e.target.value)} className={field} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">State *</label>
                <input value={form.state} onChange={(e) => set("state", e.target.value)}
                  className={field} placeholder="running" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Sub-state <span className="text-gray-400">(opt)</span></label>
                <input value={form.sub_state} onChange={(e) => set("sub_state", e.target.value)} className={field} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Dispatch Category</label>
                <select value={form.dispatch_category}
                  onChange={(e) => set("dispatch_category", e.target.value)}
                  className={field}>
                  {DISPATCH_CATS.map((c) => (
                    <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">OEE Bucket</label>
                <select value={form.oee_bucket}
                  onChange={(e) => set("oee_bucket", e.target.value)}
                  className={field}>
                  {OEE_BUCKETS.map((b) => (
                    <option key={b} value={b}>{b.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Started At</label>
                <input type="datetime-local" value={form.started_at}
                  onChange={(e) => set("started_at", e.target.value)} className={field} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Reason Code <span className="text-gray-400">(opt)</span></label>
                <input value={form.reason_code} onChange={(e) => set("reason_code", e.target.value)} className={field} />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Notes <span className="text-gray-400">(optional)</span></label>
              <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
                rows={2} className={field} />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={onClose}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button type="submit" disabled={submitting}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50">
                {submitting ? "Recording…" : "Record"}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
