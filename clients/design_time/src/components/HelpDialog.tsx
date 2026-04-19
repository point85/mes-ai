/**
 * Context-sensitive help dialog — renders a topic-specific help modal.
 */

import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";

export type HelpTopic = "products" | "materials";

interface Props {
  topic: HelpTopic;
  onClose: () => void;
}

const HELP_CONTENT: Record<HelpTopic, { title: string; body: React.ReactNode }> = {
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
