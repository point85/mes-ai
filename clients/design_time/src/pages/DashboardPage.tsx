/**
 * Dashboard — landing page for the DT-CLIENT.
 */

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p className="mt-2 text-sm text-gray-500">
        Welcome to the MES AI configuration console. Use the sidebar to navigate
        to editors for units of measure, plant model, products, and more.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <a
          href="/uom"
          className="block rounded-lg border border-gray-200 p-5 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
        >
          <h2 className="text-base font-semibold text-gray-800">
            Units of Measure
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Define SI, imperial, and custom packaging units with conversion factors.
          </p>
        </a>

        <div className="block rounded-lg border border-gray-100 bg-gray-50 p-5">
          <h2 className="text-base font-semibold text-gray-400">
            Plant Model
          </h2>
          <p className="mt-1 text-sm text-gray-400">Coming soon</p>
        </div>

        <div className="block rounded-lg border border-gray-100 bg-gray-50 p-5">
          <h2 className="text-base font-semibold text-gray-400">
            Products &amp; Routes
          </h2>
          <p className="mt-1 text-sm text-gray-400">Coming soon</p>
        </div>
      </div>
    </div>
  );
}
