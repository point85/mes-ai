/**
 * About dialog for the MES Runtime client.
 */

import { useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";

interface Props {
  onClose: () => void;
}

const FEEDBACK_ENDPOINT = "https://formspree.io/f/xlgjwrzk";

interface FeedbackDialogProps {
  onClose: () => void;
}

function FeedbackDialog({ onClose }: FeedbackDialogProps) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    const trimmed = message.trim();
    if (!trimmed) {
      setError("Enter feedback before submitting.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch(FEEDBACK_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          _subject: "MES AI Feedback",
          message: trimmed,
        }),
      });

      if (!response.ok) {
        throw new Error("Feedback submission failed.");
      }

      onClose();
    } catch {
      setError("Unable to submit feedback right now.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900">Provide Feedback</h3>
        <p className="mt-1 text-sm text-gray-500">
          Describe a comment, issue, or suggestion for MES AI.
        </p>

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={7}
          className="mt-4 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="Enter your feedback"
        />

        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Submitting..." : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AboutDialog({ onClose }: Props) {
  const [showFeedback, setShowFeedback] = useState(false);

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
        onClick={onClose}
      >
        <div
          className="relative w-full max-w-md rounded-xl bg-white p-6 shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onClose}
            className="absolute top-4 right-4 rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>

          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              RT
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">MES AI — Runtime</h2>
              <p className="text-sm text-gray-500">Version {__MES_VERSION__}</p>
            </div>
          </div>

          <p className="mb-4 text-sm leading-relaxed text-gray-700">
            Track and manage work-in-process (WIP) units and lots through production
            steps in real time. Scan serial numbers, view active WIP, monitor equipment
            status, and receive live production events via WebSocket.
          </p>

          <dl className="space-y-1 border-t pt-3 text-xs text-gray-500">
            <div className="flex justify-between">
              <dt>Release</dt>
              <dd className="font-medium text-gray-700">{__MES_VERSION__}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Standard</dt>
              <dd className="font-medium text-gray-700">ISA-95 / IEC 62264</dd>
            </div>
          </dl>

          <div className="mt-5 flex justify-end">
            <button
              type="button"
              onClick={() => setShowFeedback(true)}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
            >
              Provide Feedback
            </button>
          </div>
        </div>
      </div>

      {showFeedback && <FeedbackDialog onClose={() => setShowFeedback(false)} />}
    </>
  );
}
