/**
 * CloneDialog — reusable "Save As / Clone" modal.
 *
 * Shows a pre-filled text input for the unique identifier (code, name, symbol,
 * etc.) so the user can type a new one and clone the entity.  An optional
 * secondary field lets callers add extra required inputs (e.g. a password when
 * cloning a user).
 *
 * On confirmation the caller's `onConfirm` async function is invoked; errors
 * thrown from it are caught, formatted via formatApiError, and shown inline.
 */

import { useState, useEffect, useRef } from "react";
import { XMarkIcon, DocumentDuplicateIcon } from "@heroicons/react/24/outline";
import { formatApiError } from "../api/errors";

export interface CloneSecondaryField {
  key: string;
  label: string;
  type?: string;
  placeholder?: string;
}

interface Props {
  /** Dialog heading, e.g. "Clone Site" */
  title: string;
  /** Label for the primary identifier input, e.g. "New Code" */
  label: string;
  /** Pre-filled value from the source entity */
  initialValue: string;
  /** Optional extra field (e.g. password for user clone) */
  secondaryField?: CloneSecondaryField;
  onClose: () => void;
  /**
   * Called when the user confirms.  Should throw on failure so the dialog can
   * display the error.  On success it should return without throwing; the
   * dialog will close itself.
   */
  onConfirm: (primaryValue: string, secondaryValue?: string) => Promise<void>;
}

export default function CloneDialog({
  title,
  label,
  initialValue,
  secondaryField,
  onClose,
  onConfirm,
}: Props) {
  const [value, setValue] = useState(initialValue);
  const [secondaryValue, setSecondaryValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-select the pre-filled value so the user can immediately overtype it.
  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.select(), 60);
    return () => clearTimeout(t);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onConfirm(value.trim(), secondaryField ? secondaryValue : undefined);
      // onConfirm is responsible for closing via onClose when it succeeds.
    } catch (err) {
      setError(formatApiError(err, "Clone failed."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-lg bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <DocumentDuplicateIcon className="h-5 w-5 text-indigo-600" />
            <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}
            </label>
            <input
              ref={inputRef}
              type="text"
              value={value}
              onChange={(e) => { setValue(e.target.value); setError(null); }}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              required
              disabled={saving}
            />
          </div>

          {secondaryField && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {secondaryField.label}
              </label>
              <input
                type={secondaryField.type ?? "text"}
                value={secondaryValue}
                onChange={(e) => setSecondaryValue(e.target.value)}
                placeholder={secondaryField.placeholder}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                required
                disabled={saving}
              />
            </div>
          )}

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !value.trim()}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              <DocumentDuplicateIcon className="h-4 w-4" />
              {saving ? "Cloning…" : "Clone"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
