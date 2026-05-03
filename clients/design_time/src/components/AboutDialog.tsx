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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md rounded-xl bg-white shadow-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 rounded p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="Close"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <InformationCircleIcon className="h-8 w-8 text-indigo-600 shrink-0" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">MES AI — Design Time</h2>
            <p className="text-sm text-gray-500">Version {__MES_VERSION__}</p>
          </div>
        </div>

        <p className="text-sm text-gray-700 leading-relaxed mb-4">
          Configure and manage your MES environment: products, routes, equipment,
          work schedules, quality definitions, and more. This client provides the
          engineering and planning view of your manufacturing operations, aligned
          to the ISA-95 standard.
        </p>

        <dl className="text-xs text-gray-500 space-y-1 border-t pt-3">
          <div className="flex justify-between">
            <dt>Release</dt>
            <dd className="font-medium text-gray-700">{__MES_VERSION__}</dd>
          </div>
          <div className="flex justify-between">
            <dt>Release Date</dt>
            <dd className="font-medium text-gray-700">{__MES_RELEASE_DATE__}</dd>
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
