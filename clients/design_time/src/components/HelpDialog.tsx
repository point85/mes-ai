/**
 * Context-sensitive help dialog — renders a topic-specific help modal.
 */

import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";

export type HelpTopic =
  | "sites"
  | "equipmentClasses"
  | "storageLocations"
  | "uom"
  | "workSchedules"
  | "dataDefinitions"
  | "reasonCodes"
  | "users"
  | "roles"
  | "plugins"
  | "settings"
  | "cpgDemo"
  | "electronicsDemo"
  | "products"
  | "materials"
  | "routes"
  | "dispositions";

interface Props {
  topic: HelpTopic;
  onClose: () => void;
}

const HELP_CONTENT: Record<HelpTopic, { title: string; body: React.ReactNode }> = {
  sites: {
    title: "Sites",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Site</strong> is the top level of the ISA-95 plant model. It represents a
          manufacturing location such as a factory, plant, or major operating campus.
        </p>
        <p>
          Sites provide organizational context for the rest of the physical model. Areas,
          production lines, work cells, equipment, storage locations, schedules, and
          operational data all roll up beneath a site so planning and execution remain
          location-aware.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">ISA-95 Physical Hierarchy</h4>
        <p>
          MES AI follows the standard physical structure:
          <strong> Site → Area → Production Line → Work Cell → Equipment</strong>.
        </p>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Site</strong> — the plant or facility.</li>
          <li><strong>Area</strong> — a major section within the site, such as mixing, packaging, or SMT.</li>
          <li><strong>Production Line</strong> — a logical or physical line within an area.</li>
          <li><strong>Work Cell</strong> — the execution zone where a step is performed.</li>
          <li><strong>Equipment</strong> — the specific machine or asset that performs work.</li>
        </ul>
        <p>
          Defining the site correctly gives the rest of the hierarchy a clean foundation.
          As you model lower levels, each object inherits location context from this top
          level.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">What You Define Here</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Code and name</strong> — the stable business identity of the site.</li>
          <li><strong>Timezone</strong> — used for operational displays, schedules, and reporting alignment.</li>
          <li><strong>Address / location data</strong> — useful for administration and multi-site deployments.</li>
          <li><strong>Active state</strong> — controls whether the site remains available for current use.</li>
        </ul>

        <p>
          Use sites when you need to separate inventory, equipment, scheduling, and
          production execution across distinct facilities.
        </p>
      </div>
    ),
  },
  equipmentClasses: {
    title: "Equipment Classes",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          An <strong>Equipment Class</strong> groups equipment by capability instead of by a
          single named asset. Examples include filler, oven, printer, mixer, or tester.
        </p>
        <p>
          This follows ISA-95 Part 2 modeling: process segments can require an equipment
          class, and the system can then resolve eligible equipment at runtime based on
          what class a machine belongs to.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Why Equipment Classes Matter</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Reusable routing</strong> — routes reference capabilities, not a single machine.</li>
          <li><strong>Flexible dispatch</strong> — any qualified equipment in the class can be selected.</li>
          <li><strong>Capability modeling</strong> — class properties define what matters for that type of equipment.</li>
          <li><strong>Cleaner plant design</strong> — engineering logic stays stable even when equipment changes.</li>
        </ul>

        <p>
          Use the class detail view to define class properties and build a richer
          capability model for dispatch, validation, and future integration logic.
        </p>
      </div>
    ),
  },
  storageLocations: {
    title: "Storage Locations",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Storage Location</strong> represents a physical or logical place where
          inventory can be received, stored, staged, or shipped within a site.
        </p>
        <p>
          Storage locations are part of the inventory model. Material lots and balances
          move between these locations as receiving, putaway, staging, picking,
          consumption, and shipment transactions occur.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Common Location Types</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Receiving</strong> — inbound material arrival and initial acceptance.</li>
          <li><strong>Storage</strong> — primary warehouse or stockroom inventory.</li>
          <li><strong>Raw-in-Process</strong> — material held near or during production use.</li>
          <li><strong>Staging</strong> — short-term preparation ahead of manufacturing or shipping.</li>
          <li><strong>Shipping</strong> — outbound finished goods or transfer-ready stock.</li>
        </ul>

        <p>
          Define storage locations carefully because inventory balances, transaction
          history, and operator workflows all depend on this location structure.
        </p>
      </div>
    ),
  },
  uom: {
    title: "Units of Measure",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Unit of Measure</strong> defines how quantities are expressed across the
          MES, including materials, products, inventory balances, process values, and
          data collection points.
        </p>
        <p>
          MES AI supports both simple scalar units and composite units so engineering and
          runtime data can be represented consistently.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">What You Manage Here</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Base units</strong> — such as kilograms, pieces, seconds, or volts.</li>
          <li><strong>Conversion factors</strong> — so values can be normalized and compared correctly.</li>
          <li><strong>Composite units</strong> — quotient, product, and power-based units.</li>
          <li><strong>Type classification</strong> — mass, time, count, temperature, electrical, and more.</li>
        </ul>

        <p>
          Define units carefully because they affect BOM quantities, inventory accuracy,
          performance calculations, and validation rules throughout the system.
        </p>
      </div>
    ),
  },
  workSchedules: {
    title: "Work Schedules",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Work Schedule</strong> defines when production resources are expected to
          operate. Schedules provide the calendar context for shifts, teams, and planned
          working versus non-working time.
        </p>
        <p>
          In MES AI, schedules help align plant execution with labor planning and time-
          based analysis.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Typical Schedule Content</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Shifts</strong> — start and end times for production coverage.</li>
          <li><strong>Teams</strong> — crew or labor group assignments.</li>
          <li><strong>Rotations</strong> — repeating multi-shift or multi-team patterns.</li>
          <li><strong>Non-working periods</strong> — breaks, holidays, shutdowns, or planned downtime windows.</li>
        </ul>

        <p>
          Good schedule definitions improve reporting, OEE interpretation, shift-based
          dashboards, and future automation that depends on planned operating time.
        </p>
      </div>
    ),
  },
  dataDefinitions: {
    title: "Data Definitions",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Data Definition</strong> describes a data collection point: what should be
          measured, what type of value is expected, and what validation rules apply.
        </p>
        <p>
          These definitions are attached to process steps so operators, equipment, or
          sensors know which production data must be collected during execution.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Common Characteristics</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Data type</strong> — numeric, string, boolean, or enum.</li>
          <li><strong>Source</strong> — manual entry, equipment, or sensor feed.</li>
          <li><strong>Validation rules</strong> — limits, allowable values, and format expectations.</li>
          <li><strong>Process meaning</strong> — temperature, torque, test result, inspection note, and similar values.</li>
        </ul>

        <p>
          Treat data definitions as the contract for production data capture. Consistent
          definitions make runtime collection, genealogy, compliance, and analytics more
          reliable.
        </p>
      </div>
    ),
  },
  reasonCodes: {
    title: "Reason Codes",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Reason Code</strong> explains why a loss, downtime event, or manual state
          transition occurred. Reason codes support OEE analysis, operational reporting,
          and more disciplined plant event tracking.
        </p>
        <p>
          MES AI models reason codes hierarchically so broad categories can be refined
          into more specific causes.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Why Hierarchy Matters</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Top-level categories</strong> — such as planned downtime, failures, or minor stops.</li>
          <li><strong>Child reasons</strong> — progressively more specific operational causes.</li>
          <li><strong>OEE buckets</strong> — links losses to planned or unplanned availability analysis.</li>
          <li><strong>Reporting clarity</strong> — consistent codes make recurring issues easier to trend.</li>
        </ul>

        <p>
          Keep reason codes stable and intentional. They become part of how production,
          maintenance, and operations teams describe recurring losses.
        </p>
      </div>
    ),
  },
  users: {
    title: "Users",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>User</strong> is an individual account that can sign in to MES AI and
          perform actions according to the roles assigned to it.
        </p>
        <p>
          The Users page is where administrators manage account identity and role
          membership for engineers, operators, supervisors, and service accounts.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">What You Manage Here</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Account identity</strong> — username, full name, and email.</li>
          <li><strong>Access state</strong> — whether the account is active.</li>
          <li><strong>Credentials</strong> — password creation and reset for local auth mode.</li>
          <li><strong>Role assignments</strong> — which permission bundles the user receives.</li>
        </ul>

        <p>
          Treat user accounts as identity records and roles as permission bundles.
          Most access changes should be handled through role assignment rather than by
          creating many nearly identical roles.
        </p>
      </div>
    ),
  },
  roles: {
    title: "Roles",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Role</strong> is a named permission set used to control what a user can
          view or change in MES AI.
        </p>
        <p>
          Roles are the core of RBAC in the system. Users inherit capability through the
          roles they are assigned, rather than through one-off user-specific permission
          changes.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">How to Use Roles Well</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Model job functions</strong> — operator, engineer, admin, maintenance, and similar personas.</li>
          <li><strong>Group permissions intentionally</strong> — keep them broad enough to manage but narrow enough to control risk.</li>
          <li><strong>Reuse roles</strong> — assign a role to many users rather than cloning permission sets.</li>
          <li><strong>Protect system roles</strong> — built-in roles are part of the platform baseline and may be read-only.</li>
        </ul>

        <p>
          A good rule is to design roles around stable responsibilities, not around the
          current preferences of a single user.
        </p>
      </div>
    ),
  },
  plugins: {
    title: "Plugins",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Plugin</strong> extends MES AI without requiring every site-specific
          behavior to be hard-coded into the core application.
        </p>
        <p>
          Plugins can provide integration adapters, event handlers, custom REST endpoints,
          dispatch logic, and other extension behavior. The Plugins page is where you
          browse available plugins, install them, and manage their lifecycle.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Typical Plugin Lifecycle</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Discover</strong> — find installed or available plugins.</li>
          <li><strong>Install / enable</strong> — make the plugin available to the running system.</li>
          <li><strong>Configure</strong> — set required parameters and integration mappings.</li>
          <li><strong>Run / monitor</strong> — verify health, status, and runtime behavior.</li>
        </ul>

        <p>
          Use plugins for ERP adapters, equipment integrations, historian connections,
          and site-specific logic that should remain separate from the core platform.
        </p>
      </div>
    ),
  },
  settings: {
    title: "Settings",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          The <strong>Settings</strong> page edits server configuration exposed through the
          Design-Time Client. Changes are written to the server&apos;s <code className="text-xs bg-gray-100 px-1 rounded">.env</code>
          file and usually take effect after a restart.
        </p>
        <p>
          This page is intended for operational configuration, not business master data.
          It is where administrators manage environment-level behavior such as auth,
          feature flags, and server-side integration settings.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Use Care When Editing</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Changes affect the server</strong> — these are not just client preferences.</li>
          <li><strong>Restart may be required</strong> — many settings are loaded on startup.</li>
          <li><strong>Environment boundaries matter</strong> — dev, test, and production settings should not be mixed casually.</li>
          <li><strong>Some values stay external</strong> — database connection settings may still be managed directly in the host environment.</li>
        </ul>

        <p>
          Treat this page as controlled operational configuration. Make changes
          deliberately and understand their runtime impact before applying them.
        </p>
      </div>
    ),
  },
  cpgDemo: {
    title: "CPG Demo",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          The <strong>CPG Demo</strong> seeds a Consumer Packaged Goods example based on a
          juice bottling plant. It is intended to give you a ready-to-use reference model
          for process and lot-tracked manufacturing workflows.
        </p>
        <p>
          Running this demo seeds both the ERP-side demo data and the plant-side ISA-95
          physical model so the scenario is usable end to end.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">What It Creates</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Plant model</strong> — site, area, production line, work cells, and equipment.</li>
          <li><strong>Demo master data</strong> — products, materials, routes, and related process definitions.</li>
          <li><strong>ERP-side seed data</strong> — supporting records required for the scenario to run.</li>
          <li><strong>Equipment-material mappings</strong> — assignments that support realistic runtime behavior.</li>
        </ul>

        <p>
          Use this demo when you want a process-manufacturing example for bottling,
          batch handling, and lot-centric runtime execution.
        </p>
      </div>
    ),
  },
  electronicsDemo: {
    title: "Electronics Demo",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          The <strong>Electronics Demo</strong> seeds an SMT / PCB assembly example based on
          an electronics production plant. It is intended to demonstrate discrete and
          unit-tracked manufacturing flows.
        </p>
        <p>
          Like the CPG demo, it seeds both ERP-side demo data and the plant-side ISA-95
          physical model so the scenario can be exercised across design-time and runtime
          workflows.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">What It Creates</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Plant model</strong> — site, area, production line, work cells, and equipment.</li>
          <li><strong>Demo master data</strong> — electronics products, materials, routes, and dispositions.</li>
          <li><strong>ERP-side seed data</strong> — scenario records needed for order and execution flows.</li>
          <li><strong>Equipment-material mappings</strong> — including multi-machine SMT behavior such as dual pick-and-place.</li>
        </ul>

        <p>
          Use this demo when you want a discrete-manufacturing example for serial or
          unit-based production, inspection, and rework-oriented flows.
        </p>
      </div>
    ),
  },
  products: {
    title: "Products",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Product Definition</strong> represents the <em>finished good</em> being
          manufactured (e.g. "Shampoo Bottle 500ml", "PCB Assembly X200"). It is the{" "}
          <strong>planning / engineering view</strong> — it defines <em>how</em> to make
          something.
        </p>
        <p>
          A product owns a <strong>BOM</strong> (bill of materials listing which materials
          are consumed and in what quantities) and one or more <strong>process routes</strong>{" "}
          (the sequence of steps to produce it). Production orders reference a product.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Product Types</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Discrete</strong> — individually tracked units with serial numbers (e.g. circuit boards, assemblies).</li>
          <li><strong>Process</strong> — batch / lot-tracked production (e.g. beverages, chemicals, food).</li>
          <li><strong>Semi-Finished</strong> — intermediate sub-assemblies consumed by downstream products.</li>
          <li><strong>Configurable</strong> — products with variant options determined at order time.</li>
        </ul>

        <h4 className="font-semibold text-gray-900 pt-1">Products vs. Materials</h4>
        <p>
          <strong>Products are what you make; materials are what you use to make them.</strong>{" "}
          The BOM links the two — each BOM item says "to build this product, consume this
          material in this quantity."
        </p>
        <p>
          A product with type "finished" and a material with type "finished" often represent
          the <em>same physical item</em> from two perspectives: the product is the
          planning/engineering view (routes, BOM, version); the material is the
          inventory/logistics view (lot tracking, shelf life, balances).
        </p>
      </div>
    ),
  },
  materials: {
    title: "Materials",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Material Definition</strong> represents a raw material, component, or
          consumable that is <em>consumed</em> during manufacturing (e.g. resin pellets, PCB
          blanks, solder paste). It is the{" "}
          <strong>inventory / logistics view</strong> — a stockable item with lot tracking,
          shelf life, supplier info, and inventory balances.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Material Types</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Raw</strong> — unprocessed input materials (e.g. steel, resin, flour).</li>
          <li><strong>Intermediate</strong> — partially processed materials used in later steps.</li>
          <li><strong>Finished</strong> — completed goods tracked as inventory (mirrors a Product Definition).</li>
          <li><strong>Semi</strong> — semi-finished sub-components.</li>
          <li><strong>Consumable</strong> — items used up during production but not part of the product (e.g. lubricants, cleaning agents).</li>
          <li><strong>Packaging</strong> — boxes, labels, shrink-wrap, pallets.</li>
          <li><strong>Spare</strong> — spare parts for equipment maintenance.</li>
        </ul>

        <h4 className="font-semibold text-gray-900 pt-1">Materials vs. Products</h4>
        <p>
          <strong>Materials are what you use; products are what you make.</strong>{" "}
          When a production order completes, the finished units/lots link to both:{" "}
          <code className="text-xs bg-gray-100 px-1 rounded">product_id</code> (what was built)
          and <code className="text-xs bg-gray-100 px-1 rounded">material_id</code> (the
          inventory item that gets stocked).
        </p>
        <p>
          Many ERPs (e.g. SAP) use a single "material master" for both roles. The MES
          separates them to keep route/BOM engineering concerns distinct from
          inventory/logistics concerns.
        </p>
      </div>
    ),
  },
  routes: {
    title: "Routes",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Route</strong> defines the ordered manufacturing flow used to build a
          product. It is the process-engineering view of execution: which steps occur,
          in what sequence, and what materials, products, equipment classes, and
          dispositions are involved.
        </p>
        <p>
          In MES AI, routes are modeled as <strong>operations definitions</strong> with one or
          more <strong>process segments</strong> (steps). Products can be assigned to a route,
          and runtime WIP follows that route as units or lots move through production.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">What You Manage Here</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Route header</strong> — name, version, description, and default designation.</li>
          <li><strong>Steps</strong> — sequence, type, timing, and production behavior for each process segment.</li>
          <li><strong>Equipment requirements</strong> — which equipment classes can perform a step.</li>
          <li><strong>Material requirements</strong> — what inputs are required at each step.</li>
          <li><strong>Assignments</strong> — which products and materials are associated with the route.</li>
        </ul>

        <h4 className="font-semibold text-gray-900 pt-1">Routes vs. Products</h4>
        <p>
          <strong>Products describe what you make; routes describe how you make it.</strong>{" "}
          A product can reference one or more routes, and a route can be reused across
          multiple compatible products.
        </p>
      </div>
    ),
  },
  dispositions: {
    title: "Dispositions",
    body: (
      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        <p>
          A <strong>Disposition</strong> is a controlled outcome used to decide what should
          happen to WIP at or after a process step. Dispositions let you branch normal
          flow, place material on hold, release held WIP, or remove defective material
          from the active manufacturing path.
        </p>

        <h4 className="font-semibold text-gray-900 pt-1">Disposition Categories</h4>
        <ul className="list-disc list-inside space-y-1 text-gray-600">
          <li><strong>Route</strong> — directs WIP to the next valid path in the process flow.</li>
          <li><strong>Hold</strong> — pauses execution pending review, rework, or decision.</li>
          <li><strong>Release</strong> — returns held WIP back into an active process path.</li>
          <li><strong>Scrap</strong> — removes WIP from normal production because it should not continue.</li>
        </ul>

        <h4 className="font-semibold text-gray-900 pt-1">How They Are Used</h4>
        <p>
          Dispositions are assigned to steps and then surfaced to operators at runtime.
          They are especially useful for MRB, rework loops, inspection decisions, and
          controlled hold-and-release workflows.
        </p>
        <p>
          Keep disposition codes stable and meaningful. They often become part of
          operator vocabulary, reporting, and downstream integration logic.
        </p>
      </div>
    ),
  },
};

export default function HelpDialog({ topic, onClose }: Props) {
  const content = HELP_CONTENT[topic];

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-lg font-semibold text-gray-900">
              {content.title}
            </DialogTitle>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
          {content.body}
          <div className="mt-5 flex justify-end">
            <button
              onClick={onClose}
              className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
            >
              Close
            </button>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
