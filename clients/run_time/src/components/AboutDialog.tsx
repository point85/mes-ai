/**
 * About dialog for the MES Runtime client.
 */

import { XMarkIcon } from "@heroicons/react/24/outline";

interface Props {
  onClose: () => void;
}

export default function AboutDialog({ onClose }: Props) {
  return (
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
      </div>
    </div>
  );
}
