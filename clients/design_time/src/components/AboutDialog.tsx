/**
 * About dialog for the MES Design Time client.
 */

import { XMarkIcon, InformationCircleIcon } from "@heroicons/react/24/outline";

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
          <InformationCircleIcon className="h-8 w-8 shrink-0 text-indigo-600" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">MES AI — Design Time</h2>
            <p className="text-sm text-gray-500">Version {__MES_VERSION__}</p>
          </div>
        </div>

        <p className="mb-4 text-sm leading-relaxed text-gray-700">
          Configure and manage your MES environment: products, routes, equipment,
          work schedules, quality definitions, and more. This client provides the
          engineering and planning view of your manufacturing operations, aligned
          to the ISA-95 standard.
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
